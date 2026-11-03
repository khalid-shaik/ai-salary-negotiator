"""Currency formatting and parsing of amounts typed in plain English."""
import re

CURRENCIES = {
    "INR": {"symbol": "₹", "unit": 100_000, "unit_name": "lakhs (L)"},
    "USD": {"symbol": "$", "unit": 1_000, "unit_name": "thousands (K)"},
    "EUR": {"symbol": "€", "unit": 1_000, "unit_name": "thousands (K)"},
    "GBP": {"symbol": "£", "unit": 1_000, "unit_name": "thousands (K)"},
}


def fmt(amount: float, cur: str = "INR") -> str:
    c = CURRENCIES[cur]
    v = amount / c["unit"]
    return f"{c['symbol']}{v:,.2f} L" if cur == "INR" else f"{c['symbol']}{v:,.1f}K"


_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(lpa|lakhs?|lacs?|crores?|crs?|cr|million|k|m|l)?(?![a-z])", re.I)
_MULT = {"lpa": 1e5, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "l": 1e5, "cr": 1e7, "crs": 1e7,
         "crore": 1e7, "crores": 1e7, "k": 1e3, "m": 1e6, "million": 1e6}


def parse_amount(text: str) -> float | None:
    """Return the LAST money amount in the text (full units), or None.

    Accepts '9 LPA', '12,00,000', '95k', '1.2 cr'. Plain small numbers like '2 years' are ignored.
    """
    found = None
    for m in _NUM.finditer(text or ""):
        try:
            num = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        unit = (m.group(2) or "").lower()
        if unit:
            found = num * _MULT[unit]
        elif num >= 10_000:
            found = num
    return found
