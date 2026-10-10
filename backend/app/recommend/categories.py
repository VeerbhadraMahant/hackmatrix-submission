"""Protected vs. flexible spending categories (upgrade 3, simulate-upgrades-agent).

A recommendation must never suggest cutting spend in a PROTECTED category --
these are needs, not discretionary spend, and proposing to cut them would be
reckless advice regardless of how much it would "help" on paper. Everything
not in this set is implicitly "flexible" and fair game for
`reduce_category_spend` candidates.

Kept deliberately conservative/small so the list is easy to audit.
"""
from __future__ import annotations

from app.schemas import TxnCategory

PROTECTED_CATEGORIES: frozenset[TxnCategory] = frozenset(
    {
        TxnCategory.rent_housing,
        TxnCategory.emi_loan,
        TxnCategory.healthcare,
        TxnCategory.utilities,
    }
)


def is_flexible(category: TxnCategory) -> bool:
    """True for any category it is safe to propose cutting."""
    return category not in PROTECTED_CATEGORIES
