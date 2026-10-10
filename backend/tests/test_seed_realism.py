"""The demo personas must be skewed, deterministic and contain findable fishy data (pure: no store needed)."""
import json
import statistics
from collections import defaultdict

import pytest
from dateutil.relativedelta import relativedelta

from app.ingest.personas import PERSONA_CONFIGS, TODAY, generate_persona
from app.security import agents

RANGES = {"demo-priya": (55, 90), "demo-arjun": (30, 70), "demo-meera": (40, 80)}


def _monthly(rows, pred):
    out = defaultdict(float)
    for r in rows:
        if pred(r):
            out[(r.date.year, r.date.month)] += abs(r.amount)
    months = [(TODAY.replace(day=1) - relativedelta(months=i)) for i in range(11, 0, -1)]  # complete months only, zeros kept
    return [out[(d.year, d.month)] for d in months]


@pytest.fixture(scope="module")
def checked():
    res = {}
    for uid, cfg in PERSONA_CONFIGS.items():
        data = generate_persona(cfg)
        findings = agents.run_checks(data.transactions, data.accounts)
        res[uid] = (data, findings)
    return res


@pytest.mark.parametrize("uid", list(PERSONA_CONFIGS))
def test_deterministic(uid):
    a, b = generate_persona(PERSONA_CONFIGS[uid]), generate_persona(PERSONA_CONFIGS[uid])
    key = lambda d: [(t.date, t.amount, t.merchant, t.category, t.tags) for t in d.transactions]  # ids are random uuids
    assert key(a) == key(b)


def test_priya_lifestyle_creep(checked):
    rows = checked["demo-priya"][0].transactions
    m = _monthly(rows, lambda r: r.category in ("dining", "shopping", "entertainment") and r.amount < 0 and abs(r.amount) < 20000 and "fishy" not in (r.tags or ""))
    assert sum(m[-3:]) >= 1.3 * sum(m[:3])


def test_meera_lumpy_income(checked):
    inc = _monthly(checked["demo-meera"][0].transactions, lambda r: r.amount > 0 and r.category == "income")
    med = statistics.median(inc)
    assert sum(1 for x in inc if x < 0.25 * med) >= 2


def test_every_fishy_row_is_tagged_and_recent(checked):
    for _, (data, _) in checked.items():
        fishy = [t for t in data.transactions if "fishy" in (t.tags or "")]
        assert len(fishy) >= 4
        assert all(json.loads(t.tags)[0] == "fishy" for t in fishy)


def test_detectors_find_injected_problems(checked):
    kinds = {}
    for uid, (_, f) in checked.items():
        kinds[uid] = {k: [x["title"] for x in v] for k, v in f.items()}
    p, a, m = kinds["demo-priya"], kinds["demo-arjun"], kinds["demo-meera"]
    assert len(p["duplicate_detector"]) >= 2 and any("ICICI Home Loan EMI" in t for t in a["duplicate_detector"])
    assert any("Amaz0n" in t for t in p["merchant_verifier"]) and any("Zomat0" in t for t in a["merchant_verifier"])
    assert any("Price rise" in t for t in p["subscription_sleuth"]) and any("Overlapping" in t for t in p["subscription_sleuth"])
    assert any("Unknown Intl Wire" in t for t in p["pattern_analyst"]) and any("Croma" in t for t in m["fraud_hunter"])
    assert any("PixelGift" in t for t in p["pattern_analyst"]) and any("ATM Cash" in t for t in a["pattern_analyst"])
    assert len(m["data_guardian"]) == 3
    assert len({k for per in kinds.values() for k, v in per.items() if v}) >= 5


@pytest.mark.parametrize("uid", list(RANGES))
def test_risk_score_in_believable_range(checked, uid):
    findings = [x for v in checked[uid][1].values() for x in v]
    lo, hi = RANGES[uid]
    assert lo <= agents.risk_score(findings) <= hi


@pytest.mark.parametrize("uid", ["demo-priya", "demo-arjun"])
def test_salaried_personas_get_exactly_one_salary_per_month(uid):
    """Date jitter used to push a day-1 salary into the previous month (one month with none, one with two)."""
    rows = generate_persona(PERSONA_CONFIGS[uid]).transactions
    per_month = defaultdict(int)
    for r in rows:
        if r.merchant == "Employer Payroll":
            per_month[(r.date.year, r.date.month)] += 1
    assert per_month and set(per_month.values()) == {1}


@pytest.mark.parametrize("uid,floor", [("demo-priya", 0.03), ("demo-arjun", 0.10)])
def test_salaried_demo_personas_are_cash_positive(uid, floor):
    """The first screen a visitor sees must not show a salaried persona overspending (Meera is the stressed one)."""
    import pandas as pd

    from app.analytics.savings import trailing_savings_rate

    rows = generate_persona(PERSONA_CONFIGS[uid]).transactions
    df = pd.DataFrame([{"date": r.date, "amount": r.amount, "category": r.category} for r in rows])
    assert trailing_savings_rate(df, months=3) >= floor
