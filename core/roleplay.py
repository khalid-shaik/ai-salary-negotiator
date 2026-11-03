"""Rule-based recruiter for negotiation practice. The budget ceiling stays hidden until the end."""
import re

from .money import fmt, parse_amount

JUSTIFY = ["market", "research", "experience", "skills", "project", "certif", "competing", "another offer", "value", "bring", "achiev", "delivered"]
NON_SALARY = {"joining bonus": "joining bonus", "bonus": "joining bonus", "notice": "notice buyout", "remote": "remote flexibility",
              "wfh": "remote flexibility", "hybrid": "remote flexibility", "review": "early review", "learning": "learning budget",
              "certification": "learning budget", "leave": "extra leave", "relocation": "relocation help"}


def new_negotiation(offer: float, market_high: float, currency: str = "INR") -> dict:
    ceiling = max(offer * 1.05, min(market_high * 1.05, offer * 1.15))
    return {"offer": offer, "ceiling": ceiling, "current": offer, "round": 0, "deal": None, "walked": False,
            "justified": False, "non_salary": [], "currency": currency}


def opening(state: dict) -> str:
    return (f"Hi! Thanks for taking the time. We're excited to offer you a base of {fmt(state['offer'], state['currency'])} for the role. "
            "What are your thoughts?")


def _close(state, amount, text):
    state["deal"] = amount
    return text


def recruiter_reply(state: dict, user_text: str) -> str:
    cur = state["currency"]
    if state["deal"] is not None or state["walked"]:
        return "We've already wrapped up this conversation. You can start a new practice round."
    state["round"] += 1
    t = user_text.lower()
    if any(w in t for w in JUSTIFY):
        state["justified"] = True
    asked = sorted({v for k, v in NON_SALARY.items() if k in t})
    for a in asked:
        if a not in state["non_salary"]:
            state["non_salary"].append(a)
    amount = parse_amount(user_text)

    if re.search(r"\b(decline|walk away|not interested|no thanks)\b", t) and amount is None:
        state["walked"] = True
        return "I'm sorry to hear that. Thank you for your time, and best of luck."
    if re.search(r"\b(accept|agreed|deal|sounds good|i'm in)\b", t) and amount is None:
        return _close(state, state["current"], f"Wonderful! We'll finalise at {fmt(state['current'], cur)} and send the offer letter. Welcome aboard!")

    if amount is None:
        if asked:
            return (f"I can look into {', '.join(asked)}. To move forward, what base figure did you have in mind? "
                    f"Please share a specific number, for example '{fmt(state['current'] * 1.1, cur)}'.")
        return "I'd like to find something that works. Could you share a specific number you have in mind, and what it is based on?"

    if amount <= state["current"]:
        return _close(state, state["current"], f"That works for us. Let's go ahead at {fmt(state['current'], cur)}. Welcome aboard!")

    willing = state["ceiling"] if state["justified"] else state["offer"] + 0.5 * (state["ceiling"] - state["offer"])
    if amount <= willing or (state["round"] >= 3 and amount <= state["ceiling"]):
        extra = f" I've also noted your interest in {', '.join(state['non_salary'])}." if state["non_salary"] else ""
        return _close(state, amount, f"Let me get approval... Good news, we can do {fmt(amount, cur)}.{extra} Shall we finalise?")

    gap = state["ceiling"] - state["current"]
    if gap < 0.005 * state["offer"]:
        state["current"] = state["ceiling"]
        hint = "" if state["non_salary"] else " Is there anything else, like a joining bonus or an early review, that would help you say yes?"
        return f"{fmt(amount, cur)} is beyond what I can approve. {fmt(state['ceiling'], cur)} is the top of our range for base.{hint}"
    if state["round"] >= 4:
        state["current"] = state["ceiling"]
        return f"I've stretched as far as I can. Our best and final is {fmt(state['ceiling'], cur)}. Can we close on that?"
    counter = state["current"] + gap * (0.4, 0.6, 0.8)[min(state["round"] - 1, 2)]
    state["current"] = counter
    why = "" if state["justified"] else " It would help if you could share what your ask is based on."
    noted = f" I've noted your interest in {', '.join(state['non_salary'])}." if state["non_salary"] else ""
    return f"{fmt(amount, cur)} is above our approved range, but I can come up to {fmt(counter, cur)}.{noted}{why}"


def outcome(state: dict) -> dict:
    cur = state["currency"]
    revealed = f"The recruiter's hidden ceiling was {fmt(state['ceiling'], cur)}."
    if state["walked"] or state["deal"] is None:
        return {"deal": None, "uplift": None, "summary": "No deal was reached. " + revealed,
                "tips": ["Make a specific ask with reasons, then stay open to a counter."]}
    uplift = (state["deal"] / state["offer"] - 1) * 100
    tips = []
    if uplift < 0.5:
        tips.append("You accepted the offer as is. Next time, make a specific, justified counter before accepting.")
    elif uplift < 5:
        tips.append("A small improvement. A higher, reasoned anchor could have gone further.")
    else:
        tips.append("Strong result. You made a clear ask and backed it up.")
    if not state["justified"]:
        tips.append("Give reasons (market data, skills, projects, competing offers). It raised the recruiter's flexibility.")
    if not state["non_salary"]:
        tips.append("Try asking for non-salary items too (joining bonus, early review, learning budget).")
    gap = state["ceiling"] - state["deal"]
    tips.append("You reached the recruiter's ceiling." if gap < 0.005 * state["ceiling"] else f"There was about {fmt(gap, cur)} of room left on the table.")
    return {"deal": state["deal"], "uplift": round(uplift, 1), "summary": f"Final base: {fmt(state['deal'], cur)} ({uplift:+.1f}% vs the offer). " + revealed, "tips": tips}
