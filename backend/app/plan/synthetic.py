"""Seeded synthetic monthly history for a variable-income earner.

Months 1..TEST_START-1 (train + validation) come from `seed`; the held-out test
months come from the separate `test_seed`, so tuning on the development seed
never touches the test draws.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRAIN_END, VAL_END, TOTAL = 24, 30, 36
ANCHOR = "2022-01"  # month index 1


def _label(i: int) -> str:
    p = pd.Period(ANCHOR) + (i - 1)
    return str(p)


def generate_monthly_history(
    seed: int = 7,
    test_seed: int = 1007,
    months: int = TOTAL,
    base_income: float = 90_000.0,
    income_cv: float = 0.25,
    zero_bonus_prob: float = 0.08,
    essential_base: float = 38_000.0,
    discretionary_base: float = 22_000.0,
    rho: float = 0.4,
    disc_cv: float = 0.30,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (monthly_df, transactions_df, assumptions)."""
    rng_dev, rng_test = np.random.default_rng(seed), np.random.default_rng(test_seed)
    sigma = float(np.sqrt(np.log(1 + income_cv**2)))
    rows = []
    for i in range(1, months + 1):
        rng = rng_dev if i <= VAL_END else rng_test
        z1, z2 = rng.standard_normal(2)
        income = base_income * np.exp(sigma * z1 - sigma**2 / 2)
        if rng.random() < zero_bonus_prob:
            income *= 0.55  # occasional low month (missed bonus / lost client)
        drift = (1.05) ** (i / 12)
        essential = essential_base * drift * (1 + 0.05 * rng.standard_normal())
        disc_sigma = float(np.sqrt(np.log(1 + disc_cv**2)))
        zc = rho * z1 + np.sqrt(1 - rho**2) * z2
        discretionary = discretionary_base * np.exp(disc_sigma * zc - disc_sigma**2 / 2)
        rows.append((_label(i), float(income), float(essential), float(discretionary)))
    df = pd.DataFrame(rows, columns=["month", "income", "essential", "discretionary"])
    df.index = range(1, months + 1)

    # Transaction view of the same months (feeds the recurring-payment baseline).
    tx = []
    for i, r in df.iterrows():
        y, m = r["month"].split("-")
        d = lambda day: pd.Timestamp(int(y), int(m), day)  # noqa: E731
        tx.append((d(1), r["income"], "Employer", "income"))
        tx.append((d(3), -0.55 * r["essential"], "Landlord", "rent_housing"))
        tx.append((d(8), -0.45 * r["essential"], "Grocer", "groceries"))
        tx.append((d(12), -600.0, "Streaming", "subscriptions"))
        tx.append((d(20), -(r["discretionary"] - 600.0), f"Misc Merchant {i}x{i % 7}", "shopping"))
    txns = pd.DataFrame(tx, columns=["date", "amount", "merchant", "category"])
    txns["account_id"], txns["is_recurring"] = "synthetic", False

    assumptions = {
        "source": "synthetic, seeded; no real user data",
        "dev_seed": seed,
        "test_seed": test_seed,
        "months": months,
        "timeline": {"train": [1, TRAIN_END], "validation": [TRAIN_END + 1, VAL_END], "test": [VAL_END + 1, TOTAL]},
        "income": f"lognormal around INR {base_income:,.0f}, CV {income_cv}, {zero_bonus_prob:.0%} chance of a 45% income drop",
        "essential": f"INR {essential_base:,.0f} +/-5% noise, 5%/yr drift",
        "discretionary": f"lognormal around INR {discretionary_base:,.0f} (CV {disc_cv}), correlation {rho} with income",
        "independence": "months are independent draws (no seasonality)",
        "currency": "INR",
    }
    return df, txns, assumptions
