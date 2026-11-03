import pytest

from core import analyze, llm, money, roleplay, scripts


# ---------- money ----------
def test_fmt():
    assert money.fmt(650_000, "INR") == "₹6.50 L"
    assert money.fmt(95_000, "USD") == "$95.0K"


@pytest.mark.parametrize("text,expected", [
    ("I'd like 9 LPA", 900_000), ("12,00,000 please", 1_200_000), ("around 95k", 95_000), ("1.2 cr", 12_000_000),
    ("I have 2 years of experience", None), ("3 months notice", None), ("my current is 6 lpa and I want 9 lpa", 900_000), ("", None),
])
def test_parse_amount(text, expected):
    assert money.parse_amount(text) == expected


# ---------- analyze ----------
def test_total_comp():
    tc = analyze.total_comp({"base": 600_000, "variable": 100_000, "variable_payout": 80, "joining_bonus": 50_000,
                             "esop_value": 400_000, "esop_years": 4, "esop_haircut": 50, "benefits": 30_000})
    assert tc["variable"] == 80_000 and tc["esop"] == 50_000
    assert tc["steady"] == 760_000 and tc["year1"] == 810_000
    assert analyze.total_comp({})["steady"] == 0


def test_percentile_monotonic_and_bounded():
    vals = [1, 30, 50, 65, 85, 100, 150, 10_000]
    ps = [analyze.market_percentile(v, 50, 65, 85) for v in vals]
    assert ps == sorted(ps) and all(1 <= p <= 99 for p in ps)
    assert analyze.market_percentile(65, 50, 65, 85) == 50 and analyze.market_percentile(85, 50, 65, 85) == 75


def test_valid_market_and_hike():
    assert analyze.valid_market(5, 6, 7) and not analyze.valid_market(7, 6, 5) and not analyze.valid_market(0, 1, 2)
    assert analyze.hike_pct(120, 100) == pytest.approx(20) and analyze.hike_pct(120, 0) is None


def test_leverage_bands():
    assert analyze.leverage_score({}) == (0, "Low")
    assert analyze.leverage_score({"skills_match": True, "projects": True})[1] == "Medium"
    assert analyze.leverage_score({k: True for k in analyze.LEVERAGE}) == (100, "High")


def test_plan_ordering_and_cap():
    for fac in ({}, {"competing_offer": True, "skills_match": True, "company_urgency": True}):
        p = analyze.plan(600_000, (500_000, 650_000, 850_000), factors=fac)
        assert 600_000 <= p["target"] <= p["anchor"] <= 850_000 * 1.08 + 1
    hi = analyze.plan(600_000, (500_000, 650_000, 850_000), factors={k: True for k in analyze.LEVERAGE})
    lo = analyze.plan(600_000, (500_000, 650_000, 850_000))
    assert hi["target"] > lo["target"] and hi["leverage_band"] == "High"


def test_plan_offer_above_market_and_below_walkaway():
    top = analyze.plan(1_000_000, (500_000, 650_000, 850_000))
    assert top["verdict"].startswith("Strong") and len(top["non_salary"]) == 4
    assert top["anchor"] < 1_000_000 * 1.05
    below = analyze.plan(600_000, (500_000, 650_000, 850_000), current_base=700_000)
    assert below["walk_away"] == pytest.approx(770_000) and "Below your minimum" in below["verdict"]
    assert analyze.plan(600_000, (500_000, 650_000, 850_000))["walk_away"] == 500_000


# ---------- scripts ----------
CTX = {"name": "Alex", "recruiter": "Priya", "company": "Example Corp", "role": "Data Analyst", "location": "Hyderabad",
       "offer": "₹6.00 L", "target": "₹6.90 L", "reasons": ["3 analytics projects", "Certified in Python"], "extras": ["Joining bonus", "Early review"]}


@pytest.mark.parametrize("tone", list(scripts.TONES))
@pytest.mark.parametrize("kind", scripts.KINDS)
def test_all_scripts_render(kind, tone):
    out = scripts.build(kind, CTX, tone)
    assert out["subject"] and len(out["body"]) > 80
    assert "{" not in out["body"] and "}" not in out["body"]
    if kind != scripts.KINDS[1]:  # call plan has no signature
        assert "Alex" in out["body"] or kind == scripts.KINDS[3] or "Alex" in out["body"]


def test_counter_email_contains_figures_and_reasons():
    body = scripts.build(scripts.KINDS[0], CTX)["body"]
    for s in ("₹6.90 L", "₹6.00 L", "3 analytics projects", "Joining bonus", "Priya"):
        assert s in body


def test_critique_good_vs_bad():
    good = scripts.build(scripts.KINDS[0], CTX)["body"]
    bad = "Give me 9 LPA or else I will leave. This is my final demand."
    g, b = scripts.critique_heuristic(good), scripts.critique_heuristic(bad)
    assert g["score"] > b["score"] and g["score"] >= 85
    assert any("ultimatum" in x.lower() for x in b["improvements"])


# ---------- roleplay ----------
def _state():
    return roleplay.new_negotiation(600_000, 850_000)


def test_ceiling_bounds():
    s = _state()
    assert 600_000 * 1.05 <= s["ceiling"] <= 600_000 * 1.15


def test_reasonable_ask_with_reasons_gets_deal():
    s = _state()
    r = roleplay.recruiter_reply(s, "Based on my market research and skills I'd like 6.4 LPA")
    assert s["deal"] == 640_000 and "₹6.40 L" in r
    assert roleplay.outcome(s)["uplift"] == pytest.approx(6.7, abs=0.1)


def test_high_ask_gets_counter_then_deal_by_round_three():
    s = _state()
    roleplay.recruiter_reply(s, "I want 12 LPA")
    assert s["deal"] is None and 600_000 < s["current"] < s["ceiling"]  # concedes gradually
    roleplay.recruiter_reply(s, "I want 12 LPA, my skills are strong")
    roleplay.recruiter_reply(s, "Could you do 6.7 LPA?")
    assert s["deal"] is not None or s["round"] >= 3


def test_no_number_and_nonsalary_and_decline_and_accept():
    s = _state()
    assert "specific number" in roleplay.recruiter_reply(s, "I deserve more")
    assert "joining bonus" in roleplay.recruiter_reply(s, "Can we discuss a joining bonus?")
    assert s["non_salary"] == ["joining bonus"]
    roleplay.recruiter_reply(s, "ok I accept")
    assert s["deal"] == 600_000 and roleplay.outcome(s)["uplift"] == 0
    assert any("accepted the offer" in t for t in roleplay.outcome(s)["tips"])
    assert "already wrapped up" in roleplay.recruiter_reply(s, "hello")
    s2 = _state()
    roleplay.recruiter_reply(s2, "I'll decline, thanks")
    assert s2["walked"] and roleplay.outcome(s2)["deal"] is None


def test_counters_increase_each_round_and_stop_at_ceiling():
    s = _state()
    seen = []
    for _ in range(5):
        roleplay.recruiter_reply(s, "I want 12 LPA")
        seen.append(s["current"])
    assert seen == sorted(seen) and seen[0] < seen[-1] == s["ceiling"]
    assert "top of our range" in roleplay.recruiter_reply(s, "Please do 11 LPA")


def test_never_exceeds_ceiling():
    s = _state()
    for _ in range(6):
        roleplay.recruiter_reply(s, "I need 20 LPA given my market research")
    assert s["deal"] is None or s["deal"] <= s["ceiling"]
    assert s["current"] <= s["ceiling"] + 1


# ---------- llm ----------
def test_llm_normalizers():
    assert llm.parse_json('xx {"a": 1} yy') == {"a": 1}
    with pytest.raises(ValueError):
        llm.parse_json("nope")
    fb = {"subject": "S", "body": "B"}
    assert llm.normalize_script({"body": " new "}, fb) == {"subject": "S", "body": "new"}
    assert llm.normalize_script({}, fb) == fb
    assert llm.normalize_critique({"strengths": "x", "improvements": ["a", ""]}) == {"strengths": [], "improvements": ["a"], "rewrite": ""}
