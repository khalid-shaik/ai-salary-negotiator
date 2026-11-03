import pandas as pd
import streamlit as st

from core import analyze, llm, money, roleplay, scripts

st.set_page_config(page_title="AI Salary Negotiator", page_icon="💰", layout="wide")
ss = st.session_state

DEFAULTS = {
    "cur": "INR", "company": "", "role": "", "location": "", "base": 0.0, "variable": 0.0, "payout": 100, "bonus": 0.0,
    "esop": 0.0, "esop_years": 4, "haircut": 50, "benefits": 0.0, "m_low": 0.0, "m_mid": 0.0, "m_high": 0.0,
    "current": 0.0, "minimum": 0.0, "name": "", "recruiter": "", "reasons": "", "tone": "Warm", "kind": scripts.KINDS[0],
    "script_subject": "", "script_body": "", "notice": "", "draft": "", "critique": None, "rp": None, "rp_chat": [],
    **{f"lev_{k}": False for k in analyze.LEVERAGE},
}
for k, v in DEFAULTS.items():
    ss.setdefault(k, v)
ss.setdefault("cmp_df", pd.DataFrame([{"company": "Offer A", "base": 0.0, "variable": 0.0, "payout %": 100, "joining bonus": 0.0,
                                       "esop value": 0.0, "esop years": 4, "benefits": 0.0}]))


def unit() -> float:
    return money.CURRENCIES[ss.cur]["unit"]


def F(x: float) -> str:
    return money.fmt(x, ss.cur)


def offer_dict() -> dict:
    u = unit()
    return {"base": ss.base * u, "variable": ss.variable * u, "variable_payout": ss.payout, "joining_bonus": ss.bonus * u,
            "esop_value": ss.esop * u, "esop_years": ss.esop_years, "esop_haircut": ss.haircut, "benefits": ss.benefits * u}


def market() -> tuple[float, float, float]:
    u = unit()
    return ss.m_low * u, ss.m_mid * u, ss.m_high * u


def current_plan() -> dict:
    u = unit()
    factors = {k: ss[f"lev_{k}"] for k in analyze.LEVERAGE}
    return analyze.plan(ss.base * u, market(), ss.current * u, ss.minimum * u, factors)


def facts_text(p: dict) -> str:
    return (f"Role: {ss.role}; Company: {ss.company}; Location: {ss.location}; Current offer base: {F(ss.base * unit())}; "
            f"Target ask: {F(p['target'])}; Reasons: {'; '.join(r for r in ss.reasons.splitlines() if r.strip()) or 'n/a'}")


def load_sample():
    ss.update({"cur": "INR", "company": "Example Corp", "role": "Data Analyst", "location": "Hyderabad", "base": 6.0, "variable": 0.6,
               "payout": 80, "bonus": 0.5, "esop": 0.0, "benefits": 0.3, "m_low": 5.0, "m_mid": 6.5, "m_high": 8.5, "current": 0.0,
               "minimum": 6.0, "name": "Alex", "recruiter": "Priya",
               "reasons": "Built 3 end-to-end analytics projects in SQL, Python and Power BI\nCertified in Data Science and Python\nMy research shows market range for this role is 5-8.5 L",
               "lev_skills_match": True, "lev_projects": True, "lev_short_notice": True})
    ss.cmp_df = pd.DataFrame([
        {"company": "Example Corp", "base": 6.0, "variable": 0.6, "payout %": 80, "joining bonus": 0.5, "esop value": 0.0, "esop years": 4, "benefits": 0.3},
        {"company": "Sample Ltd", "base": 5.5, "variable": 0.0, "payout %": 100, "joining bonus": 0.0, "esop value": 2.0, "esop years": 4, "benefits": 0.5}])
    ss.rp, ss.rp_chat = None, []


def make_script():
    ss.notice = ""
    p = current_plan()
    ctx = {"name": ss.name, "recruiter": ss.recruiter, "company": ss.company, "role": ss.role, "location": ss.location,
           "offer": F(ss.base * unit()), "target": F(p["target"]), "reasons": [r.strip() for r in ss.reasons.splitlines() if r.strip()],
           "extras": [n for n, _ in p["non_salary"][:3]]}
    draft = scripts.build(ss.kind, ctx, ss.tone)
    if ss.get("polish"):
        try:
            draft = llm.polish_script(draft, ss.kind, facts_text(p), ss.tone, ss.get("model", "llama3.2"), ss.get("host"), 0.4)
        except Exception as e:
            ss.notice = f"AI polish unavailable ({e}). Showing the template version."
    ss.script_subject, ss.script_body = draft["subject"], draft["body"]


def run_critique():
    ss.notice = ""
    res = scripts.critique_heuristic(ss.draft)
    res["ai"] = None
    if ss.get("polish") and ss.draft.strip():
        try:
            res["ai"] = llm.critique_draft(ss.draft, facts_text(current_plan()), ss.get("model", "llama3.2"), ss.get("host"))
        except Exception as e:
            ss.notice = f"AI critique unavailable ({e}). Showing the offline check."
    ss.critique = res


def start_practice():
    ss.rp = roleplay.new_negotiation(ss.base * unit(), market()[2] or ss.base * unit(), ss.cur)
    ss.rp_chat = [("assistant", roleplay.opening(ss.rp))]


# ---------- sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    st.selectbox("Currency", list(money.CURRENCIES), key="cur")
    st.caption(f"Amounts are entered in {money.CURRENCIES[ss.cur]['unit_name']}.")
    st.selectbox("Message tone", list(scripts.TONES), key="tone")
    host = st.text_input("Ollama host", value="http://localhost:11434", key="host")
    installed = llm.list_models(host)
    if installed:
        st.selectbox("Model", installed, key="model")
        st.checkbox("Polish messages with AI", value=True, key="polish")
    else:
        st.session_state["polish"] = False
        st.caption("Ollama not detected. Templates, scoring and practice all work offline.")
    st.button("Load sample data", on_click=load_sample, use_container_width=True)
    st.caption("Sample figures are illustrative only. Check real market data before negotiating.")

st.title("💰 AI Salary Negotiator")
st.caption("Analyse your offer, build a negotiation plan, write the message and practise the conversation. Everything stays on your machine.")
if ss.notice:
    st.warning(ss.notice)

t1, t2, t3, t4, t5 = st.tabs(["1 · Offer & market", "2 · Strategy", "3 · Scripts", "4 · Practice", "5 · Compare offers"])

# ---------- tab 1 ----------
with t1:
    u_name = money.CURRENCIES[ss.cur]["unit_name"]
    st.subheader("The offer")
    a, b, c = st.columns(3)
    a.text_input("Company", key="company")
    b.text_input("Role", key="role")
    c.text_input("Location", key="location")
    n = dict(min_value=0.0, step=0.1, format="%.2f")
    a, b, c = st.columns(3)
    a.number_input(f"Base salary per year ({u_name})", key="base", **n)
    b.number_input("Variable pay target per year", key="variable", **n)
    c.slider("Expected variable payout %", 0, 150, key="payout")
    a, b, c = st.columns(3)
    a.number_input("Joining bonus (one-time)", key="bonus", **n)
    b.number_input("Benefits value per year (insurance, etc.)", key="benefits", **n)
    c.number_input("ESOP / stock total grant value", key="esop", **n)
    a, b = st.columns(2)
    a.slider("ESOP vesting years", 1, 6, key="esop_years")
    b.slider("ESOP risk haircut %", 0, 100, key="haircut", help="How much of the paper value you do not count on.")

    st.subheader("Market range for your role")
    st.caption("Use real data from AmbitionBox, Glassdoor, Levels.fyi or LinkedIn Salary. Enter typical low / mid / high base (about the 25th / 50th / 75th percentile).")
    a, b, c = st.columns(3)
    a.number_input("Market low", key="m_low", **n)
    b.number_input("Market mid", key="m_mid", **n)
    c.number_input("Market high", key="m_high", **n)

    if ss.base <= 0:
        st.info("Enter your offer details (or click **Load sample data**) to see the analysis.")
    else:
        tc = analyze.total_comp(offer_dict())
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Steady-state total / yr", F(tc["steady"]))
        m2.metric("Year-1 total", F(tc["year1"]), help="Includes the one-time joining bonus.")
        m3.metric("Fixed share of pay", f"{tc['fixed_share'] * 100:.0f}%")
        ok = analyze.valid_market(*market())
        if ok:
            m4.metric("Market percentile (approx.)", f"{analyze.market_percentile(tc['base'], *market())}th")
        else:
            m4.metric("Market percentile", "n/a")
            st.warning("Enter a market range where low ≤ mid ≤ high to see where your offer sits.")
        st.bar_chart(pd.Series({"Base": tc["base"] / unit(), "Variable (expected)": tc["variable"] / unit(), "ESOP / yr": tc["esop"] / unit(),
                                "Benefits": tc["benefits"] / unit(), "Joining bonus (yr 1)": tc["joining_bonus"] / unit()}, name=u_name))
        if tc["fixed_share"] < 0.8:
            st.caption("Less than 80% of this package is guaranteed fixed pay. Compare offers on fixed pay as well as total.")

# ---------- tab 2 ----------
with t2:
    st.subheader("Your leverage")
    cols = st.columns(2)
    for i, (k, (_, label)) in enumerate(analyze.LEVERAGE.items()):
        cols[i % 2].checkbox(label, key=f"lev_{k}")
    st.number_input(f"Your current base ({u_name}, 0 if none)", key="current", **n)
    st.number_input("Your minimum acceptable base (walk-away)", key="minimum", **n)
    if ss.base <= 0 or not analyze.valid_market(*market()):
        st.info("Fill in the offer and a valid market range in tab 1 first.")
    else:
        p = current_plan()
        st.divider()
        st.markdown(f"**Verdict:** {p['verdict']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Anchor (first ask)", F(p["anchor"]))
        m2.metric("Target (happy to land)", F(p["target"]))
        m3.metric("Walk-away", F(p["walk_away"]))
        m4.metric("Leverage", f"{p['leverage_band']} ({p['leverage_score']})")
        if p["hike"] is not None:
            st.caption(f"The offer is a {p['hike']:.0f}% change vs your current base. Target would be {(p['target'] / (ss.current * unit()) - 1) * 100:.0f}%.")
        for note in p["notes"]:
            st.write(f"- {note}")
        st.markdown("**Non-salary items worth asking for**")
        for name, why in p["non_salary"]:
            st.write(f"- **{name}**: {why}")
        st.caption("Rules of thumb: be grateful, name one specific number, give reasons, stay collaborative, and never lie about other offers.")

# ---------- tab 3 ----------
with t3:
    a, b, c = st.columns(3)
    a.text_input("Your name", key="name")
    b.text_input("Recruiter name", key="recruiter")
    c.selectbox("Message type", scripts.KINDS, key="kind")
    st.text_area("Your reasons (one per line: skills, projects, market data, competing offers)", key="reasons", height=110)
    st.button("✍️ Write my message", type="primary", on_click=make_script, disabled=ss.base <= 0 or not analyze.valid_market(*market()))
    if ss.script_body:
        st.text_input("Subject", key="script_subject")
        st.text_area("Message (edit freely)", key="script_body", height=340)
        st.download_button("⬇️ Download (.txt)", f"Subject: {ss.script_subject}\n\n{ss.script_body}", "negotiation_message.txt")
    st.divider()
    st.subheader("Check your own draft")
    st.text_area("Paste your draft message", key="draft", height=160)
    st.button("🔍 Review my draft", on_click=run_critique, disabled=not ss.draft.strip())
    cr = ss.critique
    if cr:
        st.metric("Draft score (offline checks)", f"{cr['score']}/100")
        l, r = st.columns(2)
        for x in cr["strengths"]:
            l.write(f"✅ {x}")
        for x in cr["improvements"]:
            r.write(f"⚠️ {x}")
        if cr["ai"]:
            st.markdown("**AI feedback**")
            for x in cr["ai"]["improvements"]:
                st.write(f"- {x}")
            if cr["ai"]["rewrite"]:
                st.text_area("AI rewrite", cr["ai"]["rewrite"], height=200)

# ---------- tab 4 ----------
with t4:
    st.subheader("Practice against a simulated recruiter")
    st.caption("The recruiter has a hidden budget. Make a specific ask with reasons, as you would in a real call. Try typing amounts like '7.5 LPA'.")
    if ss.base <= 0:
        st.info("Enter an offer in tab 1 first.")
    elif ss.rp is None:
        st.button("▶️ Start negotiation", type="primary", on_click=start_practice)
    else:
        for role_, msg in ss.rp_chat:
            with st.chat_message(role_):
                st.write(msg)
        done = ss.rp["deal"] is not None or ss.rp["walked"]
        if prompt := st.chat_input("Type your reply...", disabled=done):
            ss.rp_chat.append(("user", prompt))
            ss.rp_chat.append(("assistant", roleplay.recruiter_reply(ss.rp, prompt)))
            st.rerun()
        if done:
            res = roleplay.outcome(ss.rp)
            st.success(res["summary"]) if res["deal"] else st.info(res["summary"])
            for tip in res["tips"]:
                st.write(f"- {tip}")
        st.button("🔄 Restart", on_click=start_practice)

# ---------- tab 5 ----------
with t5:
    st.subheader("Compare offers")
    st.caption(f"Enter amounts in {u_name}. Joining bonus counts in year 1 only. ESOP is haircut by your risk % and spread over vesting years.")
    df = st.data_editor(ss.cmp_df, num_rows="dynamic", use_container_width=True, key="cmp_editor")
    rows = []
    for _, r in df.iterrows():
        if pd.isna(r["company"]) or not str(r["company"]).strip():
            continue
        g = lambda k, d=0.0: d if pd.isna(r[k]) else float(r[k])
        tc = analyze.total_comp({"base": g("base") * unit(), "variable": g("variable") * unit(), "variable_payout": g("payout %", 100),
                                 "joining_bonus": g("joining bonus") * unit(), "esop_value": g("esop value") * unit(),
                                 "esop_years": g("esop years", 4), "esop_haircut": ss.haircut, "benefits": g("benefits") * unit()})
        rows.append({"Company": r["company"], "Base": tc["base"] / unit(), "Variable": tc["variable"] / unit(), "ESOP/yr": tc["esop"] / unit(),
                     "Benefits": tc["benefits"] / unit(), "Steady total": tc["steady"] / unit(), "Year-1 total": tc["year1"] / unit()})
    if rows:
        res = pd.DataFrame(rows)
        st.dataframe(res.round(2), use_container_width=True, hide_index=True)
        st.bar_chart(res.set_index("Company")[["Base", "Variable", "ESOP/yr", "Benefits"]])
        best = res.loc[res["Steady total"].idxmax()]
        if best["Steady total"] > 0:
            st.success(f"Highest steady-state total: **{best['Company']}** at {best['Steady total']:.2f} ({u_name}). Also weigh growth, learning, team and stability.")
