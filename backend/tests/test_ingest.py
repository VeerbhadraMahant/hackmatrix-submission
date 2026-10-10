"""Tests for app.ingest: persona generator, CSV upload parser, categorizer."""
from __future__ import annotations

from collections import defaultdict

from app.core.config import get_settings
from app.ingest.categorize import categorize
from app.ingest.personas import PERSONA_CONFIGS, generate_persona, persona_dataframes
from app.ingest.upload import parse_transaction_csv
from app.schemas import TxnCategory

# ---------------------------------------------------------------------------
# Persona generator
# ---------------------------------------------------------------------------


def test_persona_monthly_income_near_stated_salary():
    for user_id, config in PERSONA_CONFIGS.items():
        if user_id == "demo-meera":  # freelancer: lumpy income by design
            continue
        data = generate_persona(config)
        income_txns = [t for t in data.transactions if t.category == TxnCategory.income.value]
        assert income_txns, f"{user_id} has no income transactions"

        # 12 monthly salary credits expected.
        assert 10 <= len(income_txns) <= 13

        total_income = sum(t.amount for t in income_txns)
        avg_monthly = total_income / len(income_txns)
        # jitter is +/-3%, so average should land very close to stated salary
        assert abs(avg_monthly - config.salary) / config.salary < 0.05


def test_persona_recurring_merchants_have_roughly_monthly_cadence():
    for user_id, config in PERSONA_CONFIGS.items():
        data = generate_persona(config)
        by_group: dict[str, list] = defaultdict(list)
        for t in data.transactions:
            if t.is_recurring and t.recurring_group_id:
                by_group[t.recurring_group_id].append(t.date)

        assert by_group, f"{user_id} produced no recurring transactions"

        for group_id, dates in by_group.items():
            if group_id == "rec-demo-meera-employer-payroll":  # freelancer: lumpy income by design
                continue
            dates = sorted(dates)
            assert len(dates) >= 8, f"{group_id} should appear ~monthly across 12 months"
            gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
            for gap in gaps:
                # nominal monthly cadence is ~28-31 days; jitter is +/-2 days
                assert 24 <= gap <= 36, f"{group_id} gap {gap}d outside monthly tolerance"


def test_persona_has_anomalies_distinct_from_recurring():
    for user_id, config in PERSONA_CONFIGS.items():
        data = generate_persona(config)
        recurring_merchants = {item.merchant for item in config.recurring}
        anomaly_merchants = {a.merchant for a in config.anomalies}
        assert anomaly_merchants, f"{user_id} should have at least one anomaly"
        assert not (anomaly_merchants & recurring_merchants)

        anomaly_txns = [t for t in data.transactions if t.merchant in anomaly_merchants]
        assert len(anomaly_txns) == len(config.anomalies)


def test_persona_dataframes_no_db_required():
    for user_id in PERSONA_CONFIGS:
        frames = persona_dataframes(user_id)
        assert set(frames) == {"accounts", "transactions", "debts", "incomes"}
        assert not frames["accounts"].empty
        assert not frames["transactions"].empty
        assert "category" in frames["transactions"].columns


def test_meera_is_fragile_persona_low_buffer():
    """Sanity check the "fragile" persona actually looks fragile: checking +
    savings balance should be small relative to monthly salary."""
    config = PERSONA_CONFIGS["demo-meera"]
    checking = next(a for a in config.accounts if a.key == "checking")
    savings = next(a for a in config.accounts if a.key == "savings")
    buffer_months = (checking.balance + savings.balance) / config.salary
    assert buffer_months < 1.0


def test_arjun_is_healthy_persona_solid_buffer():
    config = PERSONA_CONFIGS["demo-arjun"]
    checking = next(a for a in config.accounts if a.key == "checking")
    savings = next(a for a in config.accounts if a.key == "savings")
    buffer_months = (checking.balance + savings.balance) / config.salary
    assert buffer_months > 3.0


# ---------------------------------------------------------------------------
# CSV upload parser
# ---------------------------------------------------------------------------


def test_parse_csv_signed_amount_column_iso_dates():
    csv_bytes = (
        b"date,description,amount\n"
        b"2024-01-05,Swiggy Order,-450.50\n"
        b"2024-01-01,Employer Payroll,95000\n"
    )
    rows = parse_transaction_csv(csv_bytes, user_id="u1", account_id="a1")
    assert len(rows) == 2
    assert rows[0].date.isoformat() == "2024-01-05"
    assert rows[0].amount == -450.50
    assert rows[0].merchant == "Swiggy Order"
    assert rows[1].amount == 95000


def test_parse_csv_debit_credit_columns_dd_mm_yyyy():
    csv_bytes = (
        b"Transaction Date,Narration,Withdrawal Amt,Deposit Amt\n"
        b"05/01/2024,Zomato Order,350.00,\n"
        b"01/01/2024,Salary Credit,,95000.00\n"
    )
    rows = parse_transaction_csv(csv_bytes, user_id="u1", account_id="a1")
    assert len(rows) == 2
    dining_row = next(r for r in rows if "Zomato" in r.merchant)
    assert dining_row.amount == -350.00
    assert dining_row.date.isoformat() == "2024-01-05"
    salary_row = next(r for r in rows if "Salary" in r.merchant)
    assert salary_row.amount == 95000.00


def test_parse_csv_applies_categorizer_when_category_missing():
    csv_bytes = b"date,description,amount\n2024-02-10,Netflix,-649\n"
    rows = parse_transaction_csv(csv_bytes, user_id="u1", account_id="a1")
    assert rows[0].category == TxnCategory.subscriptions.value


def test_parse_csv_missing_required_columns_raises():
    csv_bytes = b"foo,bar\n1,2\n"
    try:
        parse_transaction_csv(csv_bytes)
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Categorizer
# ---------------------------------------------------------------------------

_KNOWN_MERCHANTS = [
    ("Swiggy Order #123", TxnCategory.dining),
    ("Zomato", TxnCategory.dining),
    ("Netflix", TxnCategory.subscriptions),
    ("Spotify Premium", TxnCategory.subscriptions),
    ("Disney+ Hotstar", TxnCategory.subscriptions),
    ("Uber Trip", TxnCategory.transport),
    ("Ola Cabs", TxnCategory.transport),
    ("BigBasket Grocery Order", TxnCategory.groceries),
    ("DMart", TxnCategory.groceries),
    ("Zerodha Coin SIP", TxnCategory.investment_sip),
    ("Groww Mutual Fund SIP", TxnCategory.investment_sip),
    ("HDFC Auto Loan EMI", TxnCategory.emi_loan),
    ("Prestige Lakeview Apts Rent", TxnCategory.rent_housing),
    ("Amazon.in Order", TxnCategory.shopping),
    ("Apollo Pharmacy", TxnCategory.healthcare),
    ("PVR Cinemas", TxnCategory.entertainment),
    ("Tata Power Electricity Bill", TxnCategory.utilities),
]


def test_categorize_known_merchants():
    correct = 0
    for merchant, expected in _KNOWN_MERCHANTS:
        result = categorize(merchant, -500)
        if result == expected:
            correct += 1
    assert correct >= 10, f"only {correct}/{len(_KNOWN_MERCHANTS)} known merchants categorized correctly"


def test_categorize_unknown_merchant_falls_back_to_other():
    result = categorize("Xyzzy Quux Unknown Merchant 12345", -100)
    assert result == TxnCategory.other


def test_categorize_never_raises_on_empty_merchant():
    assert categorize("", 0) == TxnCategory.other
