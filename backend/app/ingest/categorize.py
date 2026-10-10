"""Merchant -> TxnCategory categorization.

Primary path: fast rules/dictionary matching on merchant name (substring /
regex) covering common Indian merchants, plus a couple of generic amount
heuristics (e.g. EMI-shaped merchant names).

Anything the rules do not recognise becomes `TxnCategory.other`. This function must never raise.
"""
from __future__ import annotations

import re

from app.schemas import TxnCategory

# ---------------------------------------------------------------------------
# Rule-based matcher
# ---------------------------------------------------------------------------

# Ordered (pattern, category) list; first match wins. Patterns are matched
# case-insensitively against the merchant string (substring, via regex).
_RULES: list[tuple[re.Pattern, TxnCategory]] = [
    # Income
    (re.compile(r"salary|payroll|infosys|tcs payroll|wipro payroll|neft.*salary", re.I), TxnCategory.income),
    # Rent / housing
    (re.compile(r"rent|lease|landlord|apartments?|nobroker|nestaway|prestige lakeview", re.I), TxnCategory.rent_housing),
    # EMI / loans
    (re.compile(r"\bemi\b|home loan|auto loan|car loan|student loan|loan emi|hdfc.*loan|sbi.*loan|bajaj finserv", re.I), TxnCategory.emi_loan),
    # Groceries
    (re.compile(r"bigbasket|blinkit|zepto|dmart|grofers|more retail|reliance fresh|nature'?s basket|grocery", re.I), TxnCategory.groceries),
    # Dining
    (re.compile(r"swiggy|zomato|dominos|pizza hut|starbucks|cafe coffee day|ccd|barbeque nation|mcdonald|kfc|burger king|restaurant|eatery|dining", re.I), TxnCategory.dining),
    # Transport
    (re.compile(r"\buber\b|\bola\b|rapido|irctc|indigo|spicejet|vistara|metro rail|bmtc|best bus|petrol|fuel|hpcl|indian oil|bharat petroleum|fastag", re.I), TxnCategory.transport),
    # Utilities
    (re.compile(r"bescom|mseb|adani electricity|tata power|electricity|broadband|jio fiber|airtel (?!fiber)?.*(recharge|postpaid)|water bill|gas cylinder|indane|piped gas", re.I), TxnCategory.utilities),
    # Subscriptions
    (re.compile(r"netflix|spotify|hotstar|disney\+|amazon prime video|prime video|youtube premium|apple music|jio ?cinema|sonyliv|zee5|gym membership|cult\.?fit", re.I), TxnCategory.subscriptions),
    # Shopping
    (re.compile(r"amazon(?!.*prime video)|flipkart|myntra|ajio|nykaa|meesho|croma|reliance digital|decathlon", re.I), TxnCategory.shopping),
    # Healthcare
    (re.compile(r"apollo pharmacy|pharmeasy|1mg|netmeds|practo|hospital|clinic|diagnostic|pathlab|medplus", re.I), TxnCategory.healthcare),
    # Entertainment
    (re.compile(r"pvr|inox|bookmyshow|cinema|theatre|movie", re.I), TxnCategory.entertainment),
    # Investment / SIP
    (re.compile(r"zerodha|groww|coin sip|mutual fund|sip -|upstox|kuvera|nps contribution|ppf", re.I), TxnCategory.investment_sip),
    # Credit card payment
    (re.compile(r"credit card (payment|bill)|cc bill payment|card payment received", re.I), TxnCategory.credit_card_payment),
    # Transfer
    (re.compile(r"neft|imps|upi transfer|self transfer|fund transfer|atm withdrawal", re.I), TxnCategory.transfer),
    # Fees / interest
    (re.compile(r"late fee|interest charged|finance charge|annual fee|penal(ty|ty charge)|overdraft fee", re.I), TxnCategory.fees_interest),
    # School fees (recurring, treat as rent_housing-adjacent obligation -> "other" bucket has no schema slot,
    # closest fit in TxnCategory is "other" unless clearly EMI-like; keep explicit for clarity)
    (re.compile(r"school fees?|tuition fee|vidya", re.I), TxnCategory.other),
]


def matches_pattern(merchant: str, match_type: str, pattern: str) -> bool:
    """Evaluate whether a merchant name satisfies a user-defined pattern rule."""
    if not merchant or not pattern:
        return False
    m = merchant.lower().strip()
    p = pattern.lower().strip()
    if match_type == "exact":
        return m == p
    elif match_type == "starts_with":
        return m.startswith(p)
    elif match_type == "regex":
        try:
            return bool(re.search(pattern, merchant, re.I))
        except re.error:
            return False
    else:  # default "contains"
        return p in m


def _rule_match(merchant: str) -> TxnCategory | None:
    for pattern, category in _RULES:
        if pattern.search(merchant):
            return category
    return None


def _amount_heuristic(merchant: str, amount: float) -> TxnCategory | None:
    """Generic heuristics that don't depend on merchant vocabulary."""
    m = merchant.lower()
    if "emi" in m or "loan" in m:
        return TxnCategory.emi_loan
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def categorize(merchant: str, amount: float = 0.0) -> TxnCategory:
    """Return the best-guess TxnCategory for a merchant/amount pair.

    Never raises -- worst case returns TxnCategory.other.
    """
    if not merchant:
        return TxnCategory.other

    matched = _rule_match(merchant)
    if matched is not None:
        return matched

    matched = _amount_heuristic(merchant, amount)
    if matched is not None:
        return matched

    return TxnCategory.other
