"""Negotiation message templates (work offline) and a draft critic."""
import re

from .money import parse_amount

KINDS = ["Counter-offer email", "Phone call talking points", "Reply to 'this is our best offer'",
         "Request more time to decide", "Polite decline", "Accept the offer"]
TONES = {
    "Warm": {"hi": "Hi {r},", "thanks": "Thank you so much for the offer. I'm genuinely excited about the {role} role at {company}.",
             "bridge": "To help us land on something that works for both sides,", "close": "Thanks again, and I'm looking forward to the next steps.", "sign": "Warm regards,"},
    "Direct": {"hi": "Hi {r},", "thanks": "Thank you for the offer for the {role} role at {company}. I'm keen to join.",
               "bridge": "Here is where I stand:", "close": "I'd appreciate your thoughts on this.", "sign": "Best,"},
    "Formal": {"hi": "Dear {r},", "thanks": "Thank you for extending the offer for the position of {role} at {company}. I am pleased to be considered.",
               "bridge": "After careful consideration,", "close": "I would be grateful for your consideration and look forward to your reply.", "sign": "Sincerely,"},
}


def _bullets(items):
    return "\n".join(f"- {i}" for i in items)


def build(kind: str, ctx: dict, tone: str = "Warm") -> dict:
    t = TONES.get(tone, TONES["Warm"])
    f = {"r": ctx.get("recruiter") or "there", "role": ctx.get("role") or "the role", "company": ctx.get("company") or "your company"}
    hi, thanks, bridge, close = (t[k].format(**f) for k in ("hi", "thanks", "bridge", "close"))
    sign = f"{t['sign']}\n{ctx.get('name') or '[Your name]'}"
    reasons = ctx.get("reasons") or ["my skills and projects relevant to this role"]
    extras = ctx.get("extras") or []
    offer, target = ctx.get("offer", "the current offer"), ctx.get("target", "a higher figure")
    where = f" in {ctx['location']}" if ctx.get("location") else ""

    if kind == KINDS[0]:
        body = (f"{hi}\n\n{thanks}\n\n{bridge} I'd like to discuss the base compensation. Based on my research of market rates for "
                f"{f['role']}{where} and what I would bring to the team, I was hoping for a base of {target} (the offer is {offer}).\n\n"
                f"What I bring:\n{_bullets(reasons)}\n")
        if extras:
            body += f"\nIf there is limited room on base, I'd also be glad to discuss: {', '.join(extras)}.\n"
        body += f"\nWould it be possible to revisit the offer? {close}\n\n{sign}"
        return {"subject": f"Offer for {f['role']}: a quick question", "body": body}
    if kind == KINDS[1]:
        body = (f"1. Open warmly: {thanks}\n"
                f"2. State your anchor clearly: \"Based on my research and my background, I'm looking for {target}.\"\n"
                f"3. Justify in two or three points:\n{_bullets(reasons)}\n"
                "4. Then pause. Let them respond first; silence is fine.\n"
                f"5. If they say it is not possible: \"I understand. Is there flexibility on {', '.join(extras[:3]) or 'a joining bonus or an early review'}?\"\n"
                "6. If they need approval: \"Of course. When can we reconnect on this?\"\n"
                f"7. Close: \"I'm excited about this role and want to make it work. {close}\"")
        return {"subject": "Call plan", "body": body}
    if kind == KINDS[2]:
        body = (f"{hi}\n\nThank you for checking with the team and for being open with me. I understand there are limits on base, and I appreciate it.\n\n"
                f"Since I'm very interested in the role, could we look at other parts of the package? For example: {', '.join(extras[:3]) or 'a joining bonus, an early review at six months, or a learning budget'}.\n\n"
                f"If we can find something there, I'm ready to move forward quickly. {close}\n\n{sign}")
        return {"subject": f"Re: Offer for {f['role']}", "body": body}
    if kind == KINDS[3]:
        body = (f"{hi}\n\n{thanks}\n\nI'd like to give this decision the care it deserves. Would it be possible to have until [date, usually 3-5 days] to respond? "
                f"I'll be in touch sooner if I can.\n\n{close}\n\n{sign}")
        return {"subject": f"Re: Offer for {f['role']}", "body": body}
    if kind == KINDS[4]:
        body = (f"{hi}\n\nThank you very much for the offer and for the time you and the team invested in me. After careful thought, I've decided not to "
                f"move forward at this time.\n\nI truly enjoyed learning about {f['company']}, and I hope our paths cross again.\n\n{sign}")
        return {"subject": f"Re: Offer for {f['role']}", "body": body}
    body = (f"{hi}\n\nI'm delighted to accept the offer for the {f['role']} role at {f['company']} at {offer}.\n\n"
            f"Could you please share the written offer letter with the agreed terms and the joining formalities? {close}\n\n{sign}")
    return {"subject": f"Accepting the {f['role']} offer", "body": body}


def critique_heuristic(text: str) -> dict:
    t = (text or "").lower()
    words = len(t.split())
    checks = [
        (bool(re.search(r"thank|grateful|appreciate", t)), "Opens with thanks.", "Start by thanking them and showing enthusiasm."),
        (parse_amount(text) is not None, "Names a specific figure.", "Name a specific number so the ask is clear."),
        (bool(re.search(r"market|research|experience|skills|projects|certif|competing|offer from|value|bring", t)), "Gives reasons for the ask.", "Back the ask with 2-3 concrete reasons."),
        (bool(re.search(r"would it be possible|could we|would you|open to|flexib|discuss|revisit", t)), "Sounds collaborative.", "Phrase it as a question (e.g. 'Would it be possible...')."),
        (not re.search(r"or else|take it or leave|final offer|ultimatum|must|demand|i refuse", t), "No ultimatums.", "Remove ultimatums or demanding language."),
        (60 <= words <= 220, "Good length.", "Aim for 60-220 words: short enough to read quickly."),
        (bool(re.search(r"\?|look forward|let me know|your thoughts", t)), "Ends with a clear next step.", "End with a question or next step."),
    ]
    good = [g for ok, g, _ in checks if ok]
    fix = [b for ok, _, b in checks if not ok]
    return {"score": round(100 * len(good) / len(checks)), "strengths": good, "improvements": fix, "words": words}
