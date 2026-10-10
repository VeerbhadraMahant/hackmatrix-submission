"""Indian Income Tax Regime & Deductions Optimizer (Section 115BAC vs Old Regime).

Models the revised Finance Act direct-tax slabs, Standard Deduction (₹75,000 New /
₹50,000 Old), Section 87A rebate & marginal relief, and automated deduction
detection from double-entry ledger feeds (Section 80C ELSS/SIPs, Section 80D
health insurance, Section 24b home loan interest, and HRA).
"""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd

from app.schemas import (
    Debt,
    DetectedDeductions,
    TaxCalculationRequest,
    TaxDeductionsBreakdown,
    TaxOptimizationAnalysis,
    TaxRegimeCalculation,
    TaxSlabBreakdown,
    TxnCategory,
)

# Standard deductions
NEW_REGIME_STD_DEDUCTION = 75_000.0  # FY 2024-25 / FY 2025-26 salaried
OLD_REGIME_STD_DEDUCTION = 50_000.0

# Statutory deduction caps under Old Regime
LIMIT_80C = 150_000.0
LIMIT_80D = 75_000.0  # ₹25k self/family + ₹50k senior citizen parents
LIMIT_80CCD_1B = 50_000.0  # NPS additional voluntary contribution
LIMIT_24B = 200_000.0  # Self-occupied home loan interest

CESS_RATE = 0.04  # 4% Health & Education Cess

_INSURANCE_RE = re.compile(
    r"\b(insurance|lic|star health|care health|hdfc ergo|max bupa|niva bupa|tata aig|icici lombard|policybazaar)\b",
    re.IGNORECASE,
)


def _compute_slabs_tax(
    taxable_income: float,
    slab_brackets: list[tuple[float, float, float, str]],
) -> tuple[list[TaxSlabBreakdown], float]:
    """Given taxable income and slab definitions (lower, upper, rate_pct, label),
    calculates slab-by-slab tax and returns the breakdown list + raw tax before rebate."""
    breakdown: list[TaxSlabBreakdown] = []
    total_tax = 0.0

    for lower, upper, rate, label in slab_brackets:
        if taxable_income <= lower:
            breakdown.append(
                TaxSlabBreakdown(
                    slab_label=label,
                    rate_pct=rate,
                    taxable_amount_in_slab=0.0,
                    tax_amount=0.0,
                )
            )
            continue

        taxable_in_slab = min(taxable_income, upper) - lower
        slab_tax = round(taxable_in_slab * (rate / 100.0), 2)
        total_tax += slab_tax

        breakdown.append(
            TaxSlabBreakdown(
                slab_label=label,
                rate_pct=rate,
                taxable_amount_in_slab=round(taxable_in_slab, 2),
                tax_amount=slab_tax,
            )
        )

    return breakdown, round(total_tax, 2)


def compute_new_regime_tax(gross_income: float) -> TaxRegimeCalculation:
    """Calculate income tax under the New Tax Regime (Section 115BAC).
    Includes ₹75,000 standard deduction, revised slabs, Section 87A rebate
    (full rebate up to ₹7,00,000 taxable), and marginal relief.
    """
    total_deductions = min(gross_income, NEW_REGIME_STD_DEDUCTION)
    taxable_income = max(0.0, gross_income - total_deductions)

    # Revised Slabs for New Regime:
    # 0 - 3,00,000 : 0%
    # 3,00,001 - 7,00,000 : 5%
    # 7,00,001 - 10,00,000 : 10%
    # 10,00,001 - 12,00,000 : 15%
    # 12,00,001 - 15,00,000 : 20%
    # Above 15,00,000 : 30%
    slabs_def = [
        (0.0, 300_000.0, 0.0, "₹0 – ₹3,00,000 (0%)"),
        (300_000.0, 700_000.0, 5.0, "₹3,00,001 – ₹7,00,000 (5%)"),
        (700_000.0, 1_000_000.0, 10.0, "₹7,00,001 – ₹10,00,000 (10%)"),
        (1_000_000.0, 1_200_000.0, 15.0, "₹10,00,001 – ₹12,00,000 (15%)"),
        (1_200_000.0, 1_500_000.0, 20.0, "₹12,00,001 – ₹15,00,000 (20%)"),
        (1_500_000.0, float("inf"), 30.0, "Above ₹15,00,000 (30%)"),
    ]

    slabs, tax_before_rebate = _compute_slabs_tax(taxable_income, slabs_def)

    # Section 87A Rebate: if taxable income <= 7,00,000, 100% tax rebate (up to ₹25k)
    rebate = 0.0
    if taxable_income <= 700_000.0:
        rebate = tax_before_rebate
        tax_after_rebate = 0.0
    else:
        # Marginal relief: Tax payable cannot exceed (Taxable Income - ₹7,00,000)
        excess_over_7l = taxable_income - 700_000.0
        if tax_before_rebate > excess_over_7l:
            marginal_discount = tax_before_rebate - excess_over_7l
            rebate = round(marginal_discount, 2)
            tax_after_rebate = round(excess_over_7l, 2)
        else:
            tax_after_rebate = tax_before_rebate

    cess = round(tax_after_rebate * CESS_RATE, 2)
    net_tax = round(tax_after_rebate + cess, 2)
    effective_rate = round((net_tax / gross_income * 100.0), 2) if gross_income > 0 else 0.0
    monthly_take_home = round((gross_income - net_tax) / 12.0, 2)

    deductions_applied = TaxDeductionsBreakdown(
        standard_deduction=total_deductions,
        section_80c=0.0,
        section_80d=0.0,
        section_80ccd_1b_nps=0.0,
        section_24b_home_loan_interest=0.0,
        hra_exemption=0.0,
        other_deductions=0.0,
        total_deductions=total_deductions,
    )

    return TaxRegimeCalculation(
        regime="new",
        gross_income=gross_income,
        total_deductions=total_deductions,
        taxable_income=round(taxable_income, 2),
        slabs=slabs,
        tax_before_rebate=tax_before_rebate,
        rebate_87a=rebate,
        tax_after_rebate=tax_after_rebate,
        cess_4pct=cess,
        net_tax_payable=net_tax,
        effective_tax_rate_pct=effective_rate,
        monthly_take_home=monthly_take_home,
        deductions_applied=deductions_applied,
    )


def compute_old_regime_tax(
    gross_income: float,
    deductions: Optional[TaxDeductionsBreakdown] = None,
) -> TaxRegimeCalculation:
    """Calculate income tax under the Old Tax Regime.
    Applies ₹50,000 standard deduction, user deductions (80C, 80D, 80CCD, 24b, HRA),
    Old Regime slabs, and Section 87A rebate up to ₹5,00,000.
    """
    std_ded = min(gross_income, OLD_REGIME_STD_DEDUCTION)

    sec_80c = min(LIMIT_80C, deductions.section_80c if deductions else 0.0)
    sec_80d = min(LIMIT_80D, deductions.section_80d if deductions else 0.0)
    sec_nps = min(LIMIT_80CCD_1B, deductions.section_80ccd_1b_nps if deductions else 0.0)
    sec_24b = min(LIMIT_24B, deductions.section_24b_home_loan_interest if deductions else 0.0)
    hra = deductions.hra_exemption if deductions else 0.0
    other = deductions.other_deductions if deductions else 0.0

    total_deductions = round(std_ded + sec_80c + sec_80d + sec_nps + sec_24b + hra + other, 2)
    taxable_income = max(0.0, gross_income - total_deductions)

    # Old Regime Slabs:
    # 0 - 2,50,000 : 0%
    # 2,50,001 - 5,00,000 : 5%
    # 5,00,001 - 10,00,000 : 20%
    # Above 10,00,000 : 30%
    slabs_def = [
        (0.0, 250_000.0, 0.0, "₹0 – ₹2,50,000 (0%)"),
        (250_000.0, 500_000.0, 5.0, "₹2,50,001 – ₹5,00,000 (5%)"),
        (500_000.0, 1_000_000.0, 20.0, "₹5,00,001 – ₹10,00,000 (20%)"),
        (1_000_000.0, float("inf"), 30.0, "Above ₹10,00,000 (30%)"),
    ]

    slabs, tax_before_rebate = _compute_slabs_tax(taxable_income, slabs_def)

    # Section 87A Rebate: if taxable income <= 5,00,000, 100% tax rebate (up to ₹12,500)
    rebate = 0.0
    if taxable_income <= 500_000.0:
        rebate = tax_before_rebate
        tax_after_rebate = 0.0
    else:
        tax_after_rebate = tax_before_rebate

    cess = round(tax_after_rebate * CESS_RATE, 2)
    net_tax = round(tax_after_rebate + cess, 2)
    effective_rate = round((net_tax / gross_income * 100.0), 2) if gross_income > 0 else 0.0
    monthly_take_home = round((gross_income - net_tax) / 12.0, 2)

    deductions_applied = TaxDeductionsBreakdown(
        standard_deduction=std_ded,
        section_80c=sec_80c,
        section_80c_limit=LIMIT_80C,
        section_80d=sec_80d,
        section_80d_limit=LIMIT_80D,
        section_80ccd_1b_nps=sec_nps,
        section_80ccd_1b_limit=LIMIT_80CCD_1B,
        section_24b_home_loan_interest=sec_24b,
        section_24b_limit=LIMIT_24B,
        hra_exemption=hra,
        other_deductions=other,
        total_deductions=total_deductions,
    )

    return TaxRegimeCalculation(
        regime="old",
        gross_income=gross_income,
        total_deductions=total_deductions,
        taxable_income=round(taxable_income, 2),
        slabs=slabs,
        tax_before_rebate=tax_before_rebate,
        rebate_87a=rebate,
        tax_after_rebate=tax_after_rebate,
        cess_4pct=cess,
        net_tax_payable=net_tax,
        effective_tax_rate_pct=effective_rate,
        monthly_take_home=monthly_take_home,
        deductions_applied=deductions_applied,
    )


def detect_user_tax_deductions(
    df: Optional[pd.DataFrame],
    debts: list[Debt],
    monthly_income: float,
) -> DetectedDeductions:
    """Analyze transaction history and debt obligations to detect real
    80C (SIPs / ELSS / tuition), 80D (health insurance), home loan interest (24b),
    and rent paid (HRA) automatically.
    """
    sip_total = 0.0
    health_insurance = 0.0
    rent_total = 0.0

    if df is not None and not df.empty:
        work = df.copy()
        work["date"] = pd.to_datetime(work["date"])
        # trailing 12 months or annualize existing
        max_date = work["date"].max()
        twelve_mo_ago = max_date - pd.DateOffset(months=12)
        trailing_year = work[work["date"] > twelve_mo_ago]

        # 1. 80C SIP investments
        sips = trailing_year[
            (trailing_year["category"] == TxnCategory.investment_sip.value) & (trailing_year["amount"] < 0)
        ]
        sip_total = float(abs(sips["amount"].sum()))

        # If less than 12 months, annualize the median monthly SIP
        if sip_total == 0:
            all_sips = work[
                (work["category"] == TxnCategory.investment_sip.value) & (work["amount"] < 0)
            ]
            if not all_sips.empty:
                monthly_sip = abs(all_sips["amount"].median())
                sip_total = float(monthly_sip * 12.0)

        # 2. 80D Health Insurance premiums
        healthcare_txns = trailing_year[
            (trailing_year["category"] == TxnCategory.healthcare.value) & (trailing_year["amount"] < 0)
        ]
        for _, row in healthcare_txns.iterrows():
            merchant = str(row.get("merchant", ""))
            if _INSURANCE_RE.search(merchant):
                health_insurance += abs(float(row["amount"]))

        # 3. Rent paid for HRA
        rent_txns = trailing_year[
            (trailing_year["category"] == TxnCategory.rent_housing.value) & (trailing_year["amount"] < 0)
        ]
        rent_total = float(abs(rent_txns["amount"].sum()))
        if rent_total == 0:
            all_rent = work[
                (work["category"] == TxnCategory.rent_housing.value) & (work["amount"] < 0)
            ]
            if not all_rent.empty:
                rent_total = float(abs(all_rent["amount"].median()) * 12.0)

    # 4. Section 24b Home Loan Interest from Debts
    home_loan_interest = 0.0
    for d in debts:
        # Home loans typically have account_id with "home" or interest rate 8-10%
        # Calculate annual interest = principal * (apr / 100)
        is_home_loan = "home" in d.account_id.lower() or "housing" in d.account_id.lower()
        if is_home_loan:
            annual_interest = d.principal * (d.interest_rate_apr / 100.0)
            home_loan_interest += annual_interest

    return DetectedDeductions(
        section_80c_detected=round(min(LIMIT_80C, sip_total), 2),
        section_80d_detected=round(min(LIMIT_80D, health_insurance), 2),
        home_loan_interest_detected=round(min(LIMIT_24B, home_loan_interest), 2),
        rent_paid_detected=round(rent_total, 2),
    )


def calculate_break_even_deductions(
    gross_income: float,
    target_new_regime_tax: float,
    current_old_regime_deductions: float,
) -> float:
    """Finds how much ADDITIONAL deduction (beyond current deductions)
    is needed under Old Regime so that Old Regime tax matches or beats New Regime tax.
    Returns 0.0 if Old Regime is already cheaper or if break-even is unattainable.
    """
    if target_new_regime_tax <= 0:
        return 0.0

    # Binary search over additional deductions between 0 and ₹15,00,000
    low = 0.0
    high = 1_500_000.0
    best_additional = 0.0

    for _ in range(30):
        mid = (low + high) / 2.0
        trial_deductions = TaxDeductionsBreakdown(
            standard_deduction=OLD_REGIME_STD_DEDUCTION,
            section_80c=0.0,
            section_80d=0.0,
            section_80ccd_1b_nps=0.0,
            section_24b_home_loan_interest=0.0,
            other_deductions=current_old_regime_deductions + mid - OLD_REGIME_STD_DEDUCTION,
            total_deductions=current_old_regime_deductions + mid,
        )
        calc = compute_old_regime_tax(gross_income, trial_deductions)
        if calc.net_tax_payable <= target_new_regime_tax:
            best_additional = mid
            high = mid
        else:
            low = mid

    return round(best_additional, 2)


def analyze_tax_optimization(
    *,
    user_id: str,
    annual_income: float,
    df: Optional[pd.DataFrame] = None,
    debts: Optional[list[Debt]] = None,
    custom_overrides: Optional[TaxCalculationRequest] = None,
) -> TaxOptimizationAnalysis:
    """End-to-end tax comparison & optimization analyzer.

    1. Establishes gross annual income (from argument or custom override).
    2. Recovers detected deductions from transaction history & loans.
    3. Overlays any user-provided what-if custom deductions.
    4. Computes New vs Old Regime tax with slab breakdowns.
    5. Formulates actionable advice and break-even targets.
    """
    gross_income = (
        custom_overrides.gross_annual_income
        if (custom_overrides and custom_overrides.gross_annual_income is not None)
        else annual_income
    )

    detected = detect_user_tax_deductions(df, debts or [], annual_income / 12.0 if annual_income > 0 else 0.0)

    # Deductions hierarchy: user override > detected value > 0
    sec_80c = (
        custom_overrides.section_80c
        if (custom_overrides and custom_overrides.section_80c is not None)
        else detected.section_80c_detected
    )
    sec_80d = (
        custom_overrides.section_80d
        if (custom_overrides and custom_overrides.section_80d is not None)
        else detected.section_80d_detected
    )
    sec_nps = (
        custom_overrides.section_80ccd_1b_nps
        if (custom_overrides and custom_overrides.section_80ccd_1b_nps is not None)
        else 0.0
    )
    sec_24b = (
        custom_overrides.section_24b_home_loan
        if (custom_overrides and custom_overrides.section_24b_home_loan is not None)
        else detected.home_loan_interest_detected
    )
    hra = (
        custom_overrides.hra_exemption
        if (custom_overrides and custom_overrides.hra_exemption is not None)
        else min(detected.rent_paid_detected * 0.4, 180_000.0)  # estimated HRA exemption
    )
    other = (
        custom_overrides.other_deductions
        if (custom_overrides and custom_overrides.other_deductions is not None)
        else 0.0
    )

    old_deductions = TaxDeductionsBreakdown(
        standard_deduction=OLD_REGIME_STD_DEDUCTION,
        section_80c=sec_80c,
        section_80c_limit=LIMIT_80C,
        section_80d=sec_80d,
        section_80d_limit=LIMIT_80D,
        section_80ccd_1b_nps=sec_nps,
        section_80ccd_1b_limit=LIMIT_80CCD_1B,
        section_24b_home_loan_interest=sec_24b,
        section_24b_limit=LIMIT_24B,
        hra_exemption=hra,
        other_deductions=other,
        total_deductions=round(OLD_REGIME_STD_DEDUCTION + sec_80c + sec_80d + sec_nps + sec_24b + hra + other, 2),
    )

    new_calc = compute_new_regime_tax(gross_income)
    old_calc = compute_old_regime_tax(gross_income, old_deductions)

    tax_diff = round(abs(old_calc.net_tax_payable - new_calc.net_tax_payable), 2)
    monthly_delta = round(tax_diff / 12.0, 2)

    if new_calc.net_tax_payable < old_calc.net_tax_payable:
        recommended = "new"
        rationale = (
            f"The New Tax Regime saves you ₹{tax_diff:,.0f} annually (+₹{monthly_delta:,.0f}/month take-home) "
            f"thanks to lower tax slabs and the ₹75,000 standard deduction."
        )
        break_even = calculate_break_even_deductions(
            gross_income,
            new_calc.net_tax_payable,
            old_calc.total_deductions,
        )
    elif old_calc.net_tax_payable < new_calc.net_tax_payable:
        recommended = "old"
        rationale = (
            f"The Old Tax Regime saves you ₹{tax_diff:,.0f} annually (+₹{monthly_delta:,.0f}/month take-home) "
            f"due to your substantial deductions across Section 80C, 80D, and home loan/HRA benefits."
        )
        break_even = 0.0
    else:
        recommended = "new"
        rationale = (
            "Both regimes result in the exact same tax liability. The New Regime is recommended for simplicity "
            "and zero documentation requirements."
        )
        break_even = 0.0

    return TaxOptimizationAnalysis(
        user_id=user_id,
        gross_annual_income=gross_income,
        new_regime=new_calc,
        old_regime=old_calc,
        recommended_regime=recommended,
        annual_tax_savings=tax_diff,
        monthly_take_home_delta=monthly_delta,
        recommendation_rationale=rationale,
        break_even_deductions_needed=break_even,
        detected_deductions=detected,
    )
