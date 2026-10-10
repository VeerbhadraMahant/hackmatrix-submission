from datetime import date, timedelta

from app.models import TransactionRow
from app.security import agents


def _t(i, merchant, amount, days_ago=1, cat="shopping"):
    return TransactionRow(id=str(i), user_id="u", account_id="a", date=date.today() - timedelta(days=days_ago), amount=amount, merchant=merchant, category=cat)


def test_duplicate_charge_found():
    f = agents.duplicate_detector([_t(1, "Swiggy", -2499, 3), _t(2, "Swiggy", -2499, 2)], [])
    assert len(f) == 1 and f[0]["severity"] == "high"


def test_lookalike_merchant_found_and_real_one_ignored():
    assert agents.merchant_verifier([_t(1, "AMAZ0N PAY", -500)], [])
    assert not agents.merchant_verifier([_t(1, "Amazon", -500), _t(2, "Amazon Pay", -300)], [])


def test_burst_of_same_merchant_found():
    rows = [_t(i, "PixelGift", -199, 4) for i in range(5)]
    assert agents.pattern_analyst(rows, [])


def test_risk_score_is_capped_and_levelled():
    many = [{"severity": "high"}] * 10
    assert agents.risk_score(many) == 100 and agents.risk_level(100) == "high"
    assert agents.risk_score([]) == 0 and agents.risk_level(0) == "low"
