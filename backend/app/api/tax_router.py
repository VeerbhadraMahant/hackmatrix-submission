"""Indian Income Tax Regime & Deductions Optimizer API.

Endpoints:
- GET /api/tax/{user_id}/analysis: Auto-detects salary and deductions from
  the user's accounts, debts, and ledger feeds, returning an institutional
  comparison between Section 115BAC (New Regime) and the Old Tax Regime.
- POST /api/tax/{user_id}/calculate: Real-time counterfactual calculation
  supporting custom user what-if overrides (80C, 80D, 80CCD NPS, HRA, 24b).
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends

from app.analytics.tax import analyze_tax_optimization
from app.core import store
from app.core.auth import resolve_user_id
from app.ingest.snapshot import build_dashboard_snapshot
from app.models import DebtRow, TransactionRow
from app.schemas import (
    Debt,
    TaxCalculationRequest,
    TaxOptimizationAnalysis,
)

router = APIRouter()


def _transactions_df(rows: list[TransactionRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=["id", "user_id", "account_id", "date", "amount", "merchant", "category", "is_recurring", "recurring_group_id"]
        )
    df = pd.DataFrame([r.model_dump() for r in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


@router.get("/api/tax/{user_id}/analysis", response_model=TaxOptimizationAnalysis)
def get_tax_analysis(user_id: str = Depends(resolve_user_id)) -> TaxOptimizationAnalysis:
    """Analyze current tax liability under Old and New Regimes using
    automatically detected deductions from the user's financial ledger.
    """
    snap = build_dashboard_snapshot(user_id)
    txn_rows = store.query(TransactionRow, user_id=user_id)
    debt_rows = store.query(DebtRow, user_id=user_id)

    df = _transactions_df(list(txn_rows))
    debts = [
        Debt(
            id=d.id,
            user_id=user_id,
            account_id=d.account_id,
            principal=d.principal,
            interest_rate_apr=d.interest_rate_apr,
            minimum_payment=d.minimum_payment,
            due_day_of_month=d.due_day_of_month,
        )
        for d in debt_rows
    ]

    annual_income = snap.monthly_income * 12.0

    return analyze_tax_optimization(
        user_id=user_id,
        annual_income=annual_income,
        df=df,
        debts=debts,
        custom_overrides=None,
    )


@router.post("/api/tax/{user_id}/calculate", response_model=TaxOptimizationAnalysis)
def calculate_tax(
    req: TaxCalculationRequest,
    user_id: str = Depends(resolve_user_id),
) -> TaxOptimizationAnalysis:
    """Calculate tax liability with user-customized what-if deductions or
    overridden gross salary.
    """
    snap = build_dashboard_snapshot(user_id)
    txn_rows = store.query(TransactionRow, user_id=user_id)
    debt_rows = store.query(DebtRow, user_id=user_id)

    df = _transactions_df(list(txn_rows))
    debts = [
        Debt(
            id=d.id,
            user_id=user_id,
            account_id=d.account_id,
            principal=d.principal,
            interest_rate_apr=d.interest_rate_apr,
            minimum_payment=d.minimum_payment,
            due_day_of_month=d.due_day_of_month,
        )
        for d in debt_rows
    ]

    annual_income = (
        req.gross_annual_income
        if req.gross_annual_income is not None
        else snap.monthly_income * 12.0
    )

    return analyze_tax_optimization(
        user_id=user_id,
        annual_income=annual_income,
        df=df,
        debts=debts,
        custom_overrides=req,
    )
