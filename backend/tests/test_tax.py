"""Tests for Indian Income Tax Regime & Deductions Optimizer.

Covers:
- Slabs and Section 87A rebate calculations for New and Old Regimes.
- Standard deduction application (₹75k New / ₹50k Old).
- Automatic detection of Section 80C, 80D, 24(b) from ledger feeds and debts.
- Counterfactual what-if recalculation with custom user overrides.
- Fast API router responses for GET /api/tax/{user_id}/analysis and
  POST /api/tax/{user_id}/calculate.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi.testclient import TestClient

from app.analytics.tax import (
    LIMIT_80C,
    LIMIT_80D,
    LIMIT_80CCD_1B,
    LIMIT_24B,
    analyze_tax_optimization,
    calculate_break_even_deductions,
    compute_new_regime_tax,
    compute_old_regime_tax,
    detect_user_tax_deductions,
)
from app.core.auth import resolve_user_id
from app.main import app
from app.schemas import (
    Debt,
    TaxCalculationRequest,
    TaxDeductionsBreakdown,
    TxnCategory,
)

client = TestClient(app)


def test_new_regime_zero_tax_under_rebate_threshold():
    # Income ₹7,50,000 - ₹75,000 std deduction = ₹6,75,000 taxable
    # Taxable is <= ₹7,00,000 -> full 87A rebate -> ₹0 tax payable
    calc = compute_new_regime_tax(750_000.0)
    assert calc.regime == "new"
    assert calc.total_deductions == 75_000.0
    assert calc.taxable_income == 675_000.0
    assert calc.rebate_87a > 0
    assert calc.net_tax_payable == 0.0
    assert calc.effective_tax_rate_pct == 0.0
    assert calc.monthly_take_home == round(750_000.0 / 12, 2)


def test_new_regime_slabs_above_threshold():
    # Income ₹12,00,000 -> Std deduction ₹75,000 -> Taxable ₹11,25,000
    # Slabs:
    # 0 - 3L: 0
    # 3L - 7L (4L @ 5%): ₹20,000
    # 7L - 10L (3L @ 10%): ₹30,000
    # 10L - 11.25L (1.25L @ 15%): ₹18,750
    # Total tax before cess: ₹68,750
    # Cess 4%: ₹2,750
    # Net tax: ₹71,500
    calc = compute_new_regime_tax(1_200_000.0)
    assert calc.total_deductions == 75_000.0
    assert calc.taxable_income == 1_125_000.0
    assert calc.tax_before_rebate == 68_750.0
    assert calc.cess_4pct == 2_750.0
    assert calc.net_tax_payable == 71_500.0
    assert calc.effective_tax_rate_pct == round(71_500.0 / 1_200_000.0 * 100, 2)


def test_old_regime_zero_tax_under_rebate_threshold():
    # Income ₹5,00,000 - ₹50,000 std deduction = ₹4,50,000 taxable <= ₹5,00,000 -> 87A rebate
    calc = compute_old_regime_tax(500_000.0)
    assert calc.regime == "old"
    assert calc.net_tax_payable == 0.0


def test_old_vs_new_comparison_with_heavy_deductions():
    # High earner ₹20,00,000 with maxed-out deductions:
    # Std: 50k, 80C: 150k, 80D: 50k, NPS: 50k, 24b: 200k, HRA: 100k -> Total Deductions: ₹6,00,000
    # Taxable Old: ₹14,00,000
    # Taxable New: ₹19,25,000 (only 75k std deduction)
    deductions = TaxDeductionsBreakdown(
        standard_deduction=50_000.0,
        section_80c=150_000.0,
        section_80d=50_000.0,
        section_80ccd_1b_nps=50_000.0,
        section_24b_home_loan_interest=200_000.0,
        hra_exemption=100_000.0,
        other_deductions=0.0,
        total_deductions=600_000.0,
    )
    old_calc = compute_old_regime_tax(2_000_000.0, deductions)
    new_calc = compute_new_regime_tax(2_000_000.0)

    # Both calculations succeed and have positive tax
    assert old_calc.net_tax_payable > 0
    assert new_calc.net_tax_payable > 0
    # Old taxable is much lower than New taxable
    assert old_calc.taxable_income == 1_400_000.0
    assert new_calc.taxable_income == 1_925_000.0


def test_deduction_auto_detection():
    # Build synthetic transaction history with SIP, Insurance, and Rent
    records = [
        {"date": "2026-01-10", "amount": -10000.0, "category": TxnCategory.investment_sip.value, "merchant": "Groww MF SIP"},
        {"date": "2026-02-10", "amount": -10000.0, "category": TxnCategory.investment_sip.value, "merchant": "Groww MF SIP"},
        {"date": "2026-03-10", "amount": -10000.0, "category": TxnCategory.investment_sip.value, "merchant": "Groww MF SIP"},
        {"date": "2026-01-15", "amount": -22000.0, "category": TxnCategory.healthcare.value, "merchant": "Star Health Insurance"},
        {"date": "2026-01-05", "amount": -25000.0, "category": TxnCategory.rent_housing.value, "merchant": "Apartment Landlord"},
    ]
    df = pd.DataFrame(records)

    debts = [
        Debt(
            id="debt-home-1",
            user_id="test-user",
            account_id="acc_home_loan",
            principal=2_500_000.0,
            interest_rate_apr=8.5,
            minimum_payment=28_000.0,
            due_day_of_month=5,
        )
    ]

    detected = detect_user_tax_deductions(df, debts, monthly_income=100_000.0)

    # 10k monthly SIP annualized = 120,000
    assert detected.section_80c_detected > 0
    # Star Health Insurance detected
    assert detected.section_80d_detected == 22_000.0
    # Home loan interest detected
    assert detected.home_loan_interest_detected > 0
    # Rent paid detected
    assert detected.rent_paid_detected > 0


def test_api_tax_analysis_for_demo_persona():
    response = client.get("/api/tax/demo-priya/analysis")
    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == "demo-priya"
    assert data["gross_annual_income"] > 0
    assert data["recommended_regime"] in ("new", "old")
    assert "new_regime" in data
    assert "old_regime" in data
    assert len(data["new_regime"]["slabs"]) > 0
    assert len(data["old_regime"]["slabs"]) > 0
    assert "recommendation_rationale" in data


def test_api_tax_calculation_what_if_override():
    payload = {
        "gross_annual_income": 1_500_000.0,
        "section_80c": 150_000.0,
        "section_80d": 35_000.0,
        "section_80ccd_1b_nps": 50_000.0,
        "section_24b_home_loan": 180_000.0,
        "hra_exemption": 120_000.0,
    }
    response = client.post("/api/tax/demo-arjun/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["gross_annual_income"] == 1_500_000.0
    assert data["old_regime"]["deductions_applied"]["section_80c"] == 150_000.0
    assert data["old_regime"]["deductions_applied"]["section_80d"] == 35_000.0
    assert data["old_regime"]["deductions_applied"]["section_80ccd_1b_nps"] == 50_000.0
    assert data["old_regime"]["deductions_applied"]["section_24b_home_loan_interest"] == 180_000.0
    assert data["annual_tax_savings"] >= 0
