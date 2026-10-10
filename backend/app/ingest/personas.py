"""Synthetic 12-month transaction history generators for 3 demo personas.

Each persona is built from a small declarative `PersonaConfig`: a set of
accounts, a list of recurring obligations (rent/EMI/subscriptions/SIP/salary)
injected with jitter so recurring-detection has to find the periodicity
rather than read a flag, a per-category daily/weekly discretionary-spend
profile, and a handful of one-off anomalies for anomaly-detection to catch.

Two entry points:
  - `generate_persona(config) -> PersonaData` -- SQLModel row objects ready
    for bulk insert (used by `seed.py`).
  - `persona_dataframes(user_id) -> dict[str, pandas.DataFrame]` -- the same
    data as plain DataFrames, so analytics/forecast agents can import fixture
    data without touching a DB.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import pandas as pd
from dateutil.relativedelta import relativedelta

from app.models import (
    AccountRow,
    BudgetRow,
    CategorizationRuleRow,
    DebtRow,
    GoalRow,
    IncomeRow,
    TransactionRow,
)
from app.schemas import RecurrenceFrequency, TxnCategory

MONTHS_OF_HISTORY = 12
TODAY = date.today()


# ---------------------------------------------------------------------------
# Declarative persona configuration
# ---------------------------------------------------------------------------


@dataclass
class AccountSpec:
    key: str  # local reference key, e.g. "checking"
    name: str
    type: str  # AccountType value
    balance: float
    credit_limit: float | None = None
    interest_rate_apr: float | None = None


@dataclass
class RecurringItem:
    merchant: str
    category: TxnCategory
    amount: float  # signed monthly base amount (negative = outflow)
    day_of_month: int
    account_key: str
    description: str | None = None


@dataclass
class DebtSpec:
    account_key: str
    principal: float
    interest_rate_apr: float
    minimum_payment: float
    due_day_of_month: int


@dataclass
class SpendCategorySpec:
    category: TxnCategory
    merchants: list[str]
    events_per_month: tuple[int, int]  # (low, high) count of transactions
    amount_range: tuple[float, float]  # (low, high) per-transaction outflow
    account_key: str = "checking"


@dataclass
class AnomalySpec:
    months_ago: int  # 0 = most recent month
    merchant: str
    category: TxnCategory
    amount: float
    account_key: str = "checking"
    description: str = "One-off unusual purchase"


@dataclass
class PersonaConfig:
    user_id: str
    display_name: str
    city: str
    salary: float
    salary_day: int
    accounts: list[AccountSpec]
    recurring: list[RecurringItem]
    debts: list[DebtSpec]
    daily_spend: list[SpendCategorySpec]
    anomalies: list[AnomalySpec] = field(default_factory=list)
    seed: int = 42


@dataclass
class PersonaData:
    accounts: list[AccountRow]
    transactions: list[TransactionRow]
    debts: list[DebtRow]
    incomes: list[IncomeRow]
    rules: list[CategorizationRuleRow] = field(default_factory=list)
    budgets: list[BudgetRow] = field(default_factory=list)
    goals: list[GoalRow] = field(default_factory=list)



# ---------------------------------------------------------------------------
# Persona definitions
# ---------------------------------------------------------------------------


def _priya_config() -> PersonaConfig:
    return PersonaConfig(
        user_id="demo-priya",
        display_name="Priya",
        city="Bengaluru",
        salary=100_000,
        salary_day=1,
        seed=163,
        accounts=[
            AccountSpec("checking", "Priya Checking - HDFC", "checking", balance=42_000),
            AccountSpec("savings", "Priya Savings - HDFC", "savings", balance=310_000),
            AccountSpec("credit_card", "Priya Credit Card - HDFC Regalia", "credit_card", balance=-62_000, credit_limit=150_000, interest_rate_apr=42.0),
            AccountSpec("car_loan", "Priya Car Loan - HDFC Auto", "loan", balance=-380_000, interest_rate_apr=9.5),
            AccountSpec("invest", "Priya Zerodha Coin", "investment", balance=190_000),
        ],
        recurring=[
            RecurringItem("Employer Payroll", TxnCategory.income, 100_000, 1, "checking", "Monthly salary credit"),
            RecurringItem("Prestige Lakeview Apts", TxnCategory.rent_housing, -28_000, 5, "checking"),
            RecurringItem("HDFC Auto Loan EMI", TxnCategory.emi_loan, -14_500, 10, "checking"),
            RecurringItem("Netflix", TxnCategory.subscriptions, -649, 14, "credit_card"),
            RecurringItem("Spotify", TxnCategory.subscriptions, -119, 16, "credit_card"),
            RecurringItem("Amazon Prime Video", TxnCategory.subscriptions, -299, 18, "credit_card"),
            RecurringItem("JioFiber Broadband", TxnCategory.subscriptions, -999, 8, "checking"),
            RecurringItem("Cult.fit Membership", TxnCategory.subscriptions, -1499, 20, "credit_card"),
            RecurringItem("Airtel Postpaid Recharge", TxnCategory.subscriptions, -599, 22, "checking"),
            RecurringItem("Zerodha Coin SIP", TxnCategory.investment_sip, -5000, 3, "checking"),
            RecurringItem("HDFC Credit Card Bill Payment", TxnCategory.credit_card_payment, -8000, 18, "checking"),
        ],
        debts=[
            DebtSpec("car_loan", principal=380_000, interest_rate_apr=9.5, minimum_payment=14_500, due_day_of_month=10),
            DebtSpec("credit_card", principal=62_000, interest_rate_apr=42.0, minimum_payment=3_100, due_day_of_month=18),
        ],
        daily_spend=[
            SpendCategorySpec(TxnCategory.groceries, ["BigBasket", "DMart", "Zepto"], (4, 7), (400, 2200)),
            SpendCategorySpec(TxnCategory.dining, ["Swiggy", "Zomato", "Starbucks", "Third Wave Coffee"], (10, 18), (150, 1200), account_key="credit_card"),
            SpendCategorySpec(TxnCategory.transport, ["Uber", "Ola", "Indian Oil Petrol Pump"], (8, 14), (120, 900)),
            SpendCategorySpec(TxnCategory.shopping, ["Amazon.in", "Myntra", "Nykaa"], (2, 5), (500, 4500), account_key="credit_card"),
            SpendCategorySpec(TxnCategory.entertainment, ["PVR Cinemas", "BookMyShow"], (1, 3), (300, 1200), account_key="credit_card"),
            SpendCategorySpec(TxnCategory.healthcare, ["Apollo Pharmacy", "PharmEasy"], (1, 2), (200, 1500)),
        ],
        anomalies=[
            AnomalySpec(months_ago=5, merchant="Croma Electronics", category=TxnCategory.shopping, amount=-58_000, account_key="credit_card", description="One-time laptop purchase"),
            AnomalySpec(months_ago=6, merchant="Goibibo Flight Booking", category=TxnCategory.transport, amount=-22_500, account_key="credit_card", description="One-off vacation flight"),
        ],
    )


def _arjun_config() -> PersonaConfig:
    return PersonaConfig(
        user_id="demo-arjun",
        display_name="Arjun",
        city="Mumbai",
        salary=210_000,
        salary_day=1,
        seed=210,
        accounts=[
            AccountSpec("checking", "Arjun Checking - ICICI", "checking", balance=210_000),
            AccountSpec("savings", "Arjun Savings - ICICI", "savings", balance=950_000),
            AccountSpec("credit_card", "Arjun Credit Card - ICICI Amazon Pay", "credit_card", balance=-18_000, credit_limit=300_000, interest_rate_apr=39.0),
            AccountSpec("home_loan", "Arjun Home Loan - ICICI", "loan", balance=-4_200_000, interest_rate_apr=8.6),
            AccountSpec("invest", "Arjun Groww Mutual Funds", "investment", balance=610_000),
            AccountSpec("property", "Arjun Flat - Powai (est. value)", "investment", balance=6_800_000),
        ],
        recurring=[
            RecurringItem("Employer Payroll", TxnCategory.income, 210_000, 1, "checking", "Monthly salary credit"),
            RecurringItem("ICICI Home Loan EMI", TxnCategory.emi_loan, -42_000, 5, "checking"),
            RecurringItem("Greenwood High School Fees", TxnCategory.other, -18_000, 7, "checking", "Recurring school fees - child 1"),
            RecurringItem("Podar International School Fees", TxnCategory.other, -14_000, 7, "checking", "Recurring school fees - child 2"),
            RecurringItem("Netflix", TxnCategory.subscriptions, -649, 12, "credit_card"),
            RecurringItem("Amazon Prime", TxnCategory.subscriptions, -1499, 15, "credit_card"),
            RecurringItem("Hotstar Premium", TxnCategory.subscriptions, -299, 17, "credit_card"),
            RecurringItem("Tata Power Electricity Bill", TxnCategory.utilities, -4200, 9, "checking"),
            RecurringItem("Piped Gas Bill", TxnCategory.utilities, -1400, 11, "checking"),
            RecurringItem("Groww Mutual Fund SIP", TxnCategory.investment_sip, -25_000, 3, "checking"),
            RecurringItem("ICICI Credit Card Bill Payment", TxnCategory.credit_card_payment, -18_000, 20, "checking"),
        ],
        debts=[
            DebtSpec("home_loan", principal=4_200_000, interest_rate_apr=8.6, minimum_payment=42_000, due_day_of_month=5),
        ],
        daily_spend=[
            SpendCategorySpec(TxnCategory.groceries, ["DMart", "Nature's Basket", "BigBasket"], (5, 8), (600, 3000)),
            SpendCategorySpec(TxnCategory.dining, ["Zomato", "Barbeque Nation", "Cafe Coffee Day"], (5, 9), (300, 2500), account_key="credit_card"),
            SpendCategorySpec(TxnCategory.transport, ["Uber", "Indian Oil Petrol Pump", "Mumbai Metro"], (8, 12), (100, 1500)),
            SpendCategorySpec(TxnCategory.shopping, ["Amazon.in", "Reliance Digital", "Decathlon"], (2, 4), (800, 6000), account_key="credit_card"),
            SpendCategorySpec(TxnCategory.entertainment, ["PVR Cinemas", "BookMyShow"], (1, 2), (500, 1800), account_key="credit_card"),
            SpendCategorySpec(TxnCategory.healthcare, ["Apollo Pharmacy", "Practo"], (1, 3), (300, 2500)),
        ],
        anomalies=[
            AnomalySpec(months_ago=5, merchant="Taj Hotels Booking", category=TxnCategory.entertainment, amount=-45_000, account_key="credit_card", description="One-off family vacation"),
        ],
    )


def _meera_config() -> PersonaConfig:
    return PersonaConfig(
        user_id="demo-meera",
        display_name="Meera",
        city="Pune",
        salary=42_000,
        salary_day=1,
        seed=305,
        accounts=[
            AccountSpec("checking", "Meera Checking - Kotak", "checking", balance=3_200),
            AccountSpec("savings", "Meera Savings - Kotak", "savings", balance=6_500),
            AccountSpec("credit_card", "Meera Credit Card - Kotak", "credit_card", balance=-24_000, credit_limit=40_000, interest_rate_apr=45.0),
            AccountSpec("student_loan", "Meera Student Loan - SBI", "loan", balance=-260_000, interest_rate_apr=10.5),
        ],
        recurring=[
            RecurringItem("Employer Payroll", TxnCategory.income, 42_000, 1, "checking", "Monthly salary credit"),
            RecurringItem("Shared PG Rent", TxnCategory.rent_housing, -12_000, 3, "checking"),
            RecurringItem("SBI Student Loan EMI", TxnCategory.emi_loan, -6_800, 7, "checking"),
            RecurringItem("Netflix", TxnCategory.subscriptions, -649, 12, "credit_card"),
            RecurringItem("Spotify", TxnCategory.subscriptions, -119, 14, "credit_card"),
            RecurringItem("Airtel Postpaid Recharge", TxnCategory.subscriptions, -499, 19, "checking"),
            RecurringItem("Kotak Credit Card Bill Payment", TxnCategory.credit_card_payment, -2500, 22, "checking"),
        ],
        debts=[
            DebtSpec("student_loan", principal=260_000, interest_rate_apr=10.5, minimum_payment=6_800, due_day_of_month=7),
        ],
        daily_spend=[
            SpendCategorySpec(TxnCategory.groceries, ["Zepto", "Blinkit", "DMart"], (2, 4), (200, 900)),
            SpendCategorySpec(TxnCategory.dining, ["Swiggy", "Zomato", "Starbucks", "Domino's Pizza"], (14, 22), (150, 900), account_key="credit_card"),
            SpendCategorySpec(TxnCategory.transport, ["Uber", "Ola", "Rapido"], (10, 16), (80, 500)),
            SpendCategorySpec(TxnCategory.shopping, ["Myntra", "Meesho", "Ajio", "Amazon.in"], (4, 8), (400, 3500), account_key="credit_card"),
            SpendCategorySpec(TxnCategory.entertainment, ["PVR Cinemas", "BookMyShow"], (2, 4), (250, 900), account_key="credit_card"),
        ],
        anomalies=[
            AnomalySpec(months_ago=1, merchant="ATM Cash Withdrawal - Overdraft Fee", category=TxnCategory.fees_interest, amount=-590, account_key="checking", description="Overdraft fee after low balance"),
            AnomalySpec(months_ago=5, merchant="Apple Store Online", category=TxnCategory.shopping, amount=-32_000, account_key="credit_card", description="One-off impulse electronics purchase"),
        ],
    )


PERSONA_CONFIGS: dict[str, PersonaConfig] = {
    "demo-priya": _priya_config(),
    "demo-arjun": _arjun_config(),
    "demo-meera": _meera_config(),
}


# ---------------------------------------------------------------------------
# Generation engine
# ---------------------------------------------------------------------------


# Declared plan inputs for the /plan page (reserve + savings/debt goal in INR);
# api/plan_router.py uses them as defaults when a demo user passes none.
PLAN_PROFILES: dict[str, dict[str, float | int]] = {
    "demo-priya": {"reserve": 40_000, "goal_amount": 60_000, "goal_month": 6},
    "demo-arjun": {"reserve": 300_000, "goal_amount": 400_000, "goal_month": 6},
    "demo-meera": {"reserve": 5_000, "goal_amount": 60_000, "goal_month": 6},
}


def _month_anchors(months: int = MONTHS_OF_HISTORY) -> list[date]:
    """First-of-month anchors for the last `months` months, oldest first."""
    anchors = []
    for i in range(months - 1, -1, -1):
        anchors.append((TODAY.replace(day=1) - relativedelta(months=i)))
    return anchors


def _safe_day(anchor: date, day_of_month: int) -> date:
    """Clamp day_of_month to the number of days actually in `anchor`'s month."""
    next_month = anchor.replace(day=28) + timedelta(days=4)
    last_day = (next_month - timedelta(days=next_month.day)).day
    return anchor.replace(day=min(day_of_month, last_day))


# Per-persona lifestyle creep (monthly growth) on discretionary categories.
_CREEP: dict[str, tuple[float, set[str]]] = {
    "demo-priya": (1.045, {"dining", "shopping", "entertainment"}),
    "demo-arjun": (1.03, {"groceries", "dining", "shopping", "entertainment", "transport"}),
}
# Meera's freelance income by month index (oldest first): 3 strong, 2 dry, a late invoice, repeat.
_MEERA_INCOME = [1.25, 1.3, 1.2, 0.05, 0.0, 0.9, 1.3, 1.2, 1.1, 0.05, 0.0, 1.0]
_FESTIVE = {"shopping", "entertainment", "dining"}


def _lognormal(rng: random.Random, lo: float, hi: float) -> float:
    """Right-skewed amount: most near the geometric middle, a few large ones, clipped."""
    x = rng.lognormvariate(math.log(math.sqrt(lo * hi)), math.log(hi / lo) / 6)
    return min(max(x, lo * 0.7), hi * 1.15)


def _month_factor(user_id: str, category: str, month_idx: int, anchor: date) -> float:
    growth, cats = _CREEP.get(user_id, (1.0, set()))
    f = growth**month_idx if category in cats else 1.0
    if category in _FESTIVE:
        f *= {10: 1.35, 11: 1.35, 12: 0.8}.get(anchor.month, 1.0)  # Diwali spike, then post-spike dip
    return f


def _fishy_rows(user_id: str, acc: dict[str, AccountRow]) -> list[TransactionRow]:
    """Deterministic suspicious rows (tags JSON always contains "fishy") for the Evidence Room demo."""
    out: list[TransactionRow] = []

    def add(days_ago, amount, merchant, cat, kind, key="credit_card", desc=None, rec=False):
        out.append(TransactionRow(
            user_id=user_id, account_id=acc[key].id, date=TODAY - timedelta(days=days_ago),
            amount=amount, merchant=merchant, category=cat, description=desc, is_recurring=rec,
            recurring_group_id=f"rec-{user_id}-{merchant.lower().replace(' ', '-')}" if rec else None,
            tags=json.dumps(["fishy", kind]),
        ))

    if user_id == "demo-priya":
        add(12, -849.0, "Zomato", "dining", "duplicate")
        add(12, -849.0, "Zomato", "dining", "duplicate")
        add(31, -420.0, "BookMyShow", "entertainment", "duplicate")
        add(30, -420.0, "BookMyShow", "entertainment", "duplicate")
        add(20, -7499.0, "Amaz0n Pay Seller", "shopping", "lookalike")
        for k in range(12):  # Hotstar price hike 199 -> 399 -> 649, tagged only on the hiked months
            amt = (649, 399)[k] if k < 2 else 199
            add(30 * k + 3, -float(amt), "Hotstar Sports Pass", "subscriptions", "price_hike" if k < 2 else "subscription", rec=True)
        add(14, -48000.0, "Unknown Intl Wire", "other", "outlier", key="checking",
            desc="INTL WIRE OUT 02:00 IST UNVERIFIED BENEFICIARY REF X9921")
        for amt in (99, 149, 199, 299, 399, 499):  # card-testing burst
            add(5, -float(amt), "PixelGift Store", "shopping", "burst")
    elif user_id == "demo-arjun":
        for amt in (9000, 8000, 7500, 6500):  # ATM burst, 31k in one day
            add(7, -float(amt), "ATM Cash Withdrawal", "fees_interest", "cash_burst", key="checking")
        add(8, -899.0, "Zomat0", "dining", "lookalike")
        add(18, -12750.0, "Gyftr Gift Card Store", "fees_interest", "gift_card")
        add(80, -28430.0, "Star Health Insurance Premium", "fees_interest", "lump", key="checking")  # real, not fishy
        out[-1].tags = json.dumps(["lump"])
    elif user_id == "demo-meera":
        add(25, 1899.0, "Myntra Refund", "shopping", "refund_orphan")
        add(-3, -499.0, "Swiggy", "dining", "data_quality_future")
        add(11, 0.0, "Zepto", "groceries", "data_quality_zero")
        add(6, -350.0, "", "shopping", "data_quality_no_merchant")
        add(22, -94000.0, "Croma Electronics", "shopping", "outlier")
        add(40, 28500.0, "Freelance Invoice 1042 - Studio Pixel", "income", "duplicate_income", key="checking")
        add(38, 28500.0, "Freelance Invoice 1042 - Studio Pixel", "income", "duplicate_income", key="checking")
        add(16, -380.0, "Swiggy", "dining", "duplicate")
        add(15, -380.0, "Swiggy", "dining", "duplicate")
    return out


def generate_persona(config: PersonaConfig) -> PersonaData:
    rng = random.Random(config.seed)

    accounts_by_key: dict[str, AccountRow] = {}
    for spec in config.accounts:
        row = AccountRow(
            user_id=config.user_id,
            name=spec.name,
            type=spec.type,
            balance=spec.balance,
            credit_limit=spec.credit_limit,
            interest_rate_apr=spec.interest_rate_apr,
        )
        accounts_by_key[spec.key] = row

    transactions: list[TransactionRow] = []
    anchors = _month_anchors()

    # Recurring obligations, one group id per merchant so a recurring-detector
    # can also cross-check against the (deliberately absent) explicit label.
    for item in config.recurring:
        group_id = f"rec-{config.user_id}-{item.merchant.lower().replace(' ', '-')}"
        for anchor in anchors:
            jitter_days = rng.randint(-2, 2)
            jitter_pct = rng.uniform(-0.03, 0.03)
            # Jitter must never push a charge into a neighbouring month: a salary dated day 1 with -2d
            # jitter used to land on the previous month's 30th, leaving one month with no income and
            # the one before it with two -- which skewed every monthly average.
            month_end = _safe_day(anchor, 31)
            txn_date = min(max(_safe_day(anchor, item.day_of_month) + timedelta(days=jitter_days), anchor), month_end)
            if txn_date > TODAY:
                continue
            amount = round(item.amount * (1 + jitter_pct), 2)
            if config.user_id == "demo-meera" and item.category == TxnCategory.income:
                mult = _MEERA_INCOME[anchors.index(anchor)]
                if mult == 0:
                    continue
                amount = round(amount * mult, 2)
                if mult == 0.9:  # invoice paid late
                    txn_date = txn_date + timedelta(days=23)
            transactions.append(
                TransactionRow(
                    user_id=config.user_id,
                    account_id=accounts_by_key[item.account_key].id,
                    date=txn_date,
                    amount=amount,
                    merchant=item.merchant,
                    category=item.category.value,
                    description=item.description,
                    is_recurring=True,
                    recurring_group_id=group_id,
                )
            )

    # Discretionary daily/weekly spend, spread randomly across each month.
    for spec in config.daily_spend:
        for month_idx, anchor in enumerate(anchors):
            next_month = anchor.replace(day=28) + timedelta(days=4)
            days_in_month = (next_month - timedelta(days=next_month.day)).day
            days_avail = min(days_in_month, (TODAY - anchor).days + 1)  # no future-dated spend
            factor = _month_factor(config.user_id, spec.category.value, month_idx, anchor)
            # creep and festival effects scale how often she spends, keeping per-txn amounts stationary
            n_events = round(rng.randint(*spec.events_per_month) * factor * days_avail / days_in_month)
            for _ in range(n_events):
                day_offset = rng.randint(0, days_avail - 1)
                txn_date = anchor + timedelta(days=day_offset)
                amount = -round(_lognormal(rng, *spec.amount_range), 2)
                merchant = rng.choice(spec.merchants)
                transactions.append(
                    TransactionRow(
                        user_id=config.user_id,
                        account_id=accounts_by_key[spec.account_key].id,
                        date=txn_date,
                        amount=amount,
                        merchant=merchant,
                        category=spec.category.value,
                        description=None,
                        is_recurring=False,
                        recurring_group_id=None,
                    )
                )

    # One-off anomalies.
    for anomaly in config.anomalies:
        anchor = anchors[max(0, len(anchors) - 1 - anomaly.months_ago)]
        day_offset = rng.randint(0, 27)
        txn_date = anchor + timedelta(days=day_offset)
        transactions.append(
            TransactionRow(
                user_id=config.user_id,
                account_id=accounts_by_key[anomaly.account_key].id,
                date=txn_date,
                amount=anomaly.amount,
                merchant=anomaly.merchant,
                category=anomaly.category.value,
                description=anomaly.description,
                is_recurring=False,
                recurring_group_id=None,
            )
        )

    fishy = _fishy_rows(config.user_id, accounts_by_key)
    burst_days = {t.date for t in fishy if "burst" in (t.tags or "")}
    # a burst day holds only the burst, so the pattern detector sees a single merchant
    transactions = [t for t in transactions if t.date not in burst_days]
    if config.user_id == "demo-arjun":  # duplicate EMI debit: the latest EMI plus an identical copy
        emi = max((t for t in transactions if t.merchant == "ICICI Home Loan EMI"), key=lambda t: t.date)
        emi.is_recurring, emi.tags = False, json.dumps(["fishy", "duplicate_emi"])
        fishy.append(emi.model_copy(update={"id": TransactionRow().id, "date": emi.date + timedelta(days=1)}))
    transactions += fishy

    transactions.sort(key=lambda t: t.date)

    now = datetime.now(timezone.utc)
    pending_cutoff = max(0, len(transactions) - 12)
    for idx, txn in enumerate(transactions):
        cat = txn.category
        tags: list[str] = json.loads(txn.tags) if txn.tags else []  # injected rows keep their own tags
        if tags:
            pass
        elif cat == "subscriptions":
            tags = ["Subscription"]
        elif cat == "investment_sip":
            tags = ["SIP", "Tax-Deductible"]
        elif cat == "groceries":
            tags = ["Essentials"]
        elif cat == "dining":
            tags = ["Food"]
        elif cat == "rent_housing":
            tags = ["Housing", "Fixed"]
        elif cat == "utilities":
            tags = ["Bills"]
        elif cat == "healthcare":
            tags = ["Health", "80D"]
        elif cat == "shopping":
            tags = ["Discretionary"]

        if idx >= pending_cutoff:
            txn.review_status = "pending"
            txn.tags = json.dumps(tags) if tags else None
            txn.reviewed_at = None
        else:
            txn.review_status = "reviewed"
            txn.tags = json.dumps(tags) if tags else None
            txn.reviewed_at = now

    debts = [
        DebtRow(
            user_id=config.user_id,
            account_id=accounts_by_key[spec.account_key].id,
            principal=spec.principal,
            interest_rate_apr=spec.interest_rate_apr,
            minimum_payment=spec.minimum_payment,
            due_day_of_month=spec.due_day_of_month,
        )
        for spec in config.debts
    ]

    incomes = [
        IncomeRow(
            user_id=config.user_id,
            source="Employer Payroll",
            amount=config.salary,
            frequency=RecurrenceFrequency.monthly.value,
            next_date=_safe_day(anchors[-1] + relativedelta(months=1), config.salary_day),
        )
    ]

    rules = [
        CategorizationRuleRow(
            user_id=config.user_id,
            match_type="contains",
            pattern="Netflix",
            category=TxnCategory.subscriptions.value,
            tags=json.dumps(["Subscription"]),
        ),
        CategorizationRuleRow(
            user_id=config.user_id,
            match_type="contains",
            pattern="Swiggy",
            category=TxnCategory.dining.value,
            tags=json.dumps(["Food"]),
        ),
    ]

    budgets = [
        BudgetRow(
            user_id=config.user_id,
            category=TxnCategory.dining.value,
            monthly_limit=12_000,
            rollover_enabled=True,
            rollover_cap=6000,
        ),
        BudgetRow(
            user_id=config.user_id,
            category=TxnCategory.groceries.value,
            monthly_limit=15_000,
            rollover_enabled=True,
            rollover_cap=5000,
        ),
        BudgetRow(
            user_id=config.user_id,
            category=TxnCategory.transport.value,
            monthly_limit=8_000,
            rollover_enabled=True,
            rollover_cap=3000,
        ),
        BudgetRow(
            user_id=config.user_id,
            category=TxnCategory.shopping.value,
            monthly_limit=10_000,
            rollover_enabled=False,
        ),
        BudgetRow(
            user_id=config.user_id,
            category=TxnCategory.subscriptions.value,
            monthly_limit=5_000,
            rollover_enabled=False,
        ),
    ]

    if config.user_id == "demo-priya":
        goals = [
            GoalRow(
                user_id=config.user_id,
                name="Emergency Fund",
                target_amount=500_000,
                target_date=_safe_day(anchors[-1] + relativedelta(months=8), 15),
                current_amount=180_000,
                cover_key="emergency_fund",
                funding_account_id=accounts_by_key["savings"].id if "savings" in accounts_by_key else None,
                auto_track=True,
            ),
            GoalRow(
                user_id=config.user_id,
                name="Dream Car (EV)",
                target_amount=1_800_000,
                target_date=_safe_day(anchors[-1] + relativedelta(months=18), 1),
                current_amount=350_000,
                cover_key="dream_car",
                funding_account_id=None,
                auto_track=False,
            ),
            GoalRow(
                user_id=config.user_id,
                name="Japan Cherry Blossom Trip",
                target_amount=350_000,
                target_date=_safe_day(anchors[-1] + relativedelta(months=12), 1),
                current_amount=120_000,
                cover_key="luxury_travel",
                funding_account_id=None,
                auto_track=False,
            ),
        ]
    elif config.user_id == "demo-arjun":
        goals = [
            GoalRow(
                user_id=config.user_id,
                name="Kids Higher Education",
                target_amount=2_500_000,
                target_date=_safe_day(anchors[-1] + relativedelta(months=36), 1),
                current_amount=610_000,
                cover_key="higher_education",
                funding_account_id=accounts_by_key["invest"].id if "invest" in accounts_by_key else None,
                auto_track=True,
            ),
            GoalRow(
                user_id=config.user_id,
                name="Family Europe Vacation",
                target_amount=600_000,
                target_date=_safe_day(anchors[-1] + relativedelta(months=14), 1),
                current_amount=200_000,
                cover_key="luxury_travel",
                funding_account_id=None,
                auto_track=False,
            ),
        ]
    elif config.user_id == "demo-meera":
        goals = [
            GoalRow(
                user_id=config.user_id,
                name="Pay Off Student Loan Early",
                target_amount=260_000,
                target_date=_safe_day(anchors[-1] + relativedelta(months=24), 1),
                current_amount=45_000,
                cover_key="emergency_fund",
                funding_account_id=accounts_by_key["savings"].id if "savings" in accounts_by_key else None,
                auto_track=True,
            ),
            GoalRow(
                user_id=config.user_id,
                name="MacBook Pro M-Series",
                target_amount=180_000,
                target_date=_safe_day(anchors[-1] + relativedelta(months=9), 1),
                current_amount=35_000,
                cover_key="tech_setup",
                funding_account_id=None,
                auto_track=False,
            ),
        ]
    else:
        goals = [
            GoalRow(
                user_id=config.user_id,
                name="Emergency Fund",
                target_amount=300_000,
                target_date=_safe_day(anchors[-1] + relativedelta(months=12), 1),
                current_amount=50_000,
                cover_key="emergency_fund",
                funding_account_id=None,
                auto_track=False,
            )
        ]

    return PersonaData(
        accounts=list(accounts_by_key.values()),
        transactions=transactions,
        debts=debts,
        incomes=incomes,
        rules=rules,
        budgets=budgets,
        goals=goals,
    )



def generate_all_personas() -> dict[str, PersonaData]:
    return {user_id: generate_persona(cfg) for user_id, cfg in PERSONA_CONFIGS.items()}


# ---------------------------------------------------------------------------
# DataFrame fixtures (no DB required) -- for analytics-agent / forecast-sim-agent
# ---------------------------------------------------------------------------


def persona_dataframes(user_id: str) -> dict[str, pd.DataFrame]:
    """Return {"accounts", "transactions", "debts", "incomes"} as plain
    pandas DataFrames for a given demo user_id, with no DB dependency."""
    if user_id not in PERSONA_CONFIGS:
        raise KeyError(f"Unknown demo persona user_id: {user_id!r}")
    data = generate_persona(PERSONA_CONFIGS[user_id])

    accounts_df = pd.DataFrame([a.model_dump() for a in data.accounts])
    transactions_df = pd.DataFrame([t.model_dump() for t in data.transactions])
    debts_df = pd.DataFrame([d.model_dump() for d in data.debts])
    incomes_df = pd.DataFrame([i.model_dump() for i in data.incomes])

    if not transactions_df.empty:
        transactions_df["date"] = pd.to_datetime(transactions_df["date"])
        transactions_df = transactions_df.sort_values("date").reset_index(drop=True)

    return {
        "accounts": accounts_df,
        "transactions": transactions_df,
        "debts": debts_df,
        "incomes": incomes_df,
    }


def all_persona_dataframes() -> dict[str, dict[str, pd.DataFrame]]:
    return {user_id: persona_dataframes(user_id) for user_id in PERSONA_CONFIGS}
