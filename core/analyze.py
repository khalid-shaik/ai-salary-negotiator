"""Offer analysis and negotiation planning (pure functions, no LLM)."""

LEVERAGE = {
    "competing_offer": (25, "You hold a competing offer"),
    "skills_match": (20, "Your skills closely match the job description"),
    "company_urgency": (15, "The company needs to fill the role urgently"),
    "projects": (10, "You have strong projects, certifications or achievements"),
    "short_notice": (10, "You can join quickly"),
    "internal_champion": (10, "A referral or the hiring manager is championing you"),
    "high_current": (10, "Your current pay is already high"),
}
UPLIFT = {"Low": (0.03, 0.06), "Medium": (0.06, 0.12), "High": (0.12, 0.20)}

NON_SALARY = [
    ("Joining bonus", "Often easier to approve than a higher base, and a one-time cost for the company."),
    ("Early salary review (6 months)", "Gets you to your target without moving the starting base."),
    ("Notice-period buyout", "Useful if you are leaving a job with a long notice period."),
    ("Learning / certification budget", "Cheap for the company and valuable for your career."),
    ("Role level or title", "Starts you on a higher band, so future raises compound."),
    ("Remote / hybrid flexibility", "Can be worth a lot without any cash cost."),
    ("ESOP or bonus guarantee", "Ask for the variable to be guaranteed in year one."),
    ("Extra leave or relocation help", "Easy wins if base is capped."),
]


def total_comp(o: dict) -> dict:
    base = float(o.get("base", 0) or 0)
    variable = float(o.get("variable", 0) or 0) * float(o.get("variable_payout", 100) or 0) / 100
    bonus = float(o.get("joining_bonus", 0) or 0)
    years = max(1.0, float(o.get("esop_years", 4) or 4))
    esop = float(o.get("esop_value", 0) or 0) * (1 - float(o.get("esop_haircut", 50) or 0) / 100) / years
    benefits = float(o.get("benefits", 0) or 0)
    steady = base + variable + esop + benefits
    return {"base": base, "variable": variable, "esop": esop, "benefits": benefits, "joining_bonus": bonus,
            "steady": steady, "year1": steady + bonus, "fixed_share": base / steady if steady else 0.0}


def valid_market(low: float, mid: float, high: float) -> bool:
    return 0 < low <= mid <= high


def market_percentile(value: float, low: float, mid: float, high: float) -> int:
    """Approximate percentile. low/mid/high are treated as the 25th/50th/75th percentiles."""
    if value <= 0:
        return 1
    if value <= low:
        p = 25 * value / low
    elif value <= mid:
        p = 25 + 25 * (value - low) / max(mid - low, 1e-9)
    elif value <= high:
        p = 50 + 25 * (value - mid) / max(high - mid, 1e-9)
    else:
        p = 75 + 100 * (value - high) / high
    return int(round(max(1, min(99, p))))


def hike_pct(offer_base: float, current_base: float) -> float | None:
    return (offer_base / current_base - 1) * 100 if current_base and current_base > 0 else None


def leverage_score(factors: dict) -> tuple[int, str]:
    score = sum(w for k, (w, _) in LEVERAGE.items() if factors.get(k))
    return score, "High" if score >= 60 else "Medium" if score >= 30 else "Low"


def plan(offer_base: float, market: tuple[float, float, float], current_base: float = 0.0,
         minimum: float = 0.0, factors: dict | None = None) -> dict:
    low, mid, high = market
    score, band = leverage_score(factors or {})
    cap = high * 1.08  # above this an ask loses credibility
    lo_u, hi_u = UPLIFT[band]
    notes = [f"Leverage is {band.lower()} ({score}/100), so a realistic ask is about {lo_u * 100:.0f}-{hi_u * 100:.0f}% above the offer."]
    if offer_base >= high:
        anchor, target = offer_base * 1.03, offer_base * 1.02
        notes.append("The offer is already at or above the top of the market range. Focus on non-salary items.")
    else:
        anchor = min(offer_base * (1 + hi_u + 0.03), cap)
        target = min(offer_base * (1 + (lo_u + hi_u) / 2), anchor)
        if anchor == cap:
            notes.append("Your anchor is capped just above the top of the market range to stay credible.")
    walk_away = max(minimum, current_base * 1.10 if current_base else 0.0) or low
    pos = market_percentile(offer_base, low, mid, high)
    if offer_base < walk_away:
        verdict = "Below your minimum: negotiate firmly or be ready to decline."
    elif offer_base < low:
        verdict = "Below the typical market range."
    elif offer_base < mid:
        verdict = "Slightly below the market midpoint: worth negotiating."
    elif offer_base < high:
        verdict = "Competitive. A modest negotiation is still reasonable."
    else:
        verdict = "Strong offer at the top of the range."
    reasons = [text for key, (_, text) in LEVERAGE.items() if (factors or {}).get(key)]
    return {"anchor": anchor, "target": target, "walk_away": walk_away, "percentile": pos, "verdict": verdict,
            "leverage_score": score, "leverage_band": band, "reasons": reasons, "notes": notes,
            "hike": hike_pct(offer_base, current_base),
            "non_salary": NON_SALARY[:4] if offer_base >= high else NON_SALARY}
