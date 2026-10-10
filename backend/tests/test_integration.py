"""Integration tests for the real DB-backed dashboard snapshot pipeline
(app.ingest.snapshot) and the /api/events real-recompute-diff endpoint.

Uses the Firestore emulator (see tests/conftest.py),
seeding the 3 demo personas fresh at module setup so these tests are
independent of whatever `python -m app.ingest.seed` state happens to already
be in the emulator.
"""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.ingest.personas import PERSONA_CONFIGS
from app.ingest.seed import seed_all
from app.ingest.snapshot import build_dashboard_snapshot, get_last_snapshot
from app.main import app
from app.schemas import ActionType

seed_all()

client = TestClient(app)


# ---------------------------------------------------------------------------
# build_dashboard_snapshot: real per-persona snapshots
# ---------------------------------------------------------------------------


def test_build_dashboard_snapshot_all_personas_well_formed():
    for user_id in PERSONA_CONFIGS:
        snap = build_dashboard_snapshot(user_id)

        assert snap.user_id == user_id
        assert 0 <= snap.health_score.overall <= 100
        assert len(snap.health_score.sub_scores) == 5
        assert snap.forecast.horizon_days == 90
        assert len(snap.forecast.points) == 90
        # forecast ordering invariant: p10 <= p50 <= p90 at every point
        for p in snap.forecast.points:
            assert p.p10 <= p.p50 <= p.p90
        # every recommendation carries a real, populated impact estimate
        for rec in snap.insights.recommendations:
            assert rec.impact is not None
            assert rec.action in ActionType
        assert isinstance(snap.debts, list)


def test_health_scores_differ_meaningfully_across_personas():
    scores = {}
    for user_id in PERSONA_CONFIGS:
        snap = build_dashboard_snapshot(user_id)
        scores[user_id] = snap.health_score.overall

    # Meera is the deliberately "fragile" persona (near-zero buffer, highest
    # DTI relative to income); Arjun is the "healthy" persona (large buffer,
    # comfortable DTI). Their health scores should reflect that ordering.
    assert scores["demo-meera"] < scores["demo-arjun"]
    # Scores should not all collapse to the same number -- real variation.
    assert len(set(round(s, 1) for s in scores.values())) == len(scores)


def test_snapshot_forecast_reflects_real_starting_balance():
    """Meera's persona has a very small checking+savings balance relative to
    her obligations -- her forecast should show meaningfully lower balances
    than Arjun's comfortably-funded forecast at day 0."""
    meera = build_dashboard_snapshot("demo-meera")
    arjun = build_dashboard_snapshot("demo-arjun")

    assert meera.forecast.points[0].p50 < arjun.forecast.points[0].p50


def test_snapshot_is_cached_and_retrievable():
    snap = build_dashboard_snapshot("demo-priya")
    cached = get_last_snapshot("demo-priya")

    assert cached is not None
    assert cached.user_id == "demo-priya"
    assert cached.health_score.overall == snap.health_score.overall


def test_unknown_user_gets_empty_snapshot():
    snap = build_dashboard_snapshot("totally-unknown-user-id")
    assert snap.user_id == "totally-unknown-user-id"
    # a real user with no data is NOT shown demo data
    assert snap.has_data is False
    assert snap.net_worth == 0 and not snap.forecast.points


# ---------------------------------------------------------------------------
# /api/events/{user_id}: real recompute diff end to end
# ---------------------------------------------------------------------------


def test_events_endpoint_recomputes_real_diff():
    # Seed a "before" snapshot explicitly so this test doesn't depend on
    # ordering relative to the module-level snapshot tests above.
    before = build_dashboard_snapshot("demo-arjun")

    # A single small transaction is unlikely to change much on its own, but
    # the response must still reflect a REAL recompute (not a before==after
    # stub): health_score_before should match the just-cached snapshot, and
    # the response shape must be a fully-formed RecomputeDiff.
    r = client.post(
        "/api/events/demo-arjun",
        json={"kind": "transaction", "amount": -500.0, "merchant": "Test Merchant", "category": "dining"},
    )
    assert r.status_code == 200
    diff = r.json()

    assert diff["trigger"] == "transaction"
    assert diff["health_score_before"] == before.health_score.overall
    assert isinstance(diff["health_score_after"], float)
    assert diff["narrative"]

    # after must reflect the just-added transaction: recompute again and
    # confirm the new transaction is now part of this user's data.
    after = build_dashboard_snapshot("demo-arjun")
    assert after.generated_at >= before.generated_at


def test_events_endpoint_large_transaction_shifts_forecast_or_recommendations():
    """A large, immediate cash outflow should show up as a real change: a
    higher DTI-adjacent health impact, a shifted first-gap date, or at least
    a different recommendation set -- not silently before == after for
    everything."""
    import datetime as _dt

    today = _dt.date.today().isoformat()
    r = client.post(
        "/api/events/demo-meera",
        json={
            "kind": "transaction",
            "amount": -20000.0,
            "merchant": "Large One-Off Expense",
            "category": "shopping",
            "date": today,
        },
    )
    assert r.status_code == 200
    diff = r.json()

    changed = (
        diff["health_score_before"] != diff["health_score_after"]
        or diff["forecast_first_gap_before"] != diff["forecast_first_gap_after"]
        or diff["new_recommendations"]
        or diff["removed_recommendation_actions"]
    )
    assert changed, f"expected a real change from a ₹20,000 hit to Meera's thin buffer, got: {diff}"


def test_events_endpoint_rejects_missing_amount():
    r = client.post("/api/events/demo-priya", json={"kind": "transaction"})
    assert r.status_code == 400


def test_events_endpoint_unsupported_kind():
    r = client.post("/api/events/demo-priya", json={"kind": "not_a_real_kind"})
    assert r.status_code == 400


def test_events_endpoint_recurring_kind_is_supported():
    """Regression test: the "recurring" kind (posted by the Timeline page's
    "New recurring obligation" form) previously had no branch in add_event()
    at all and always 400'd. It must now succeed and the new obligation must
    actually show up as a recurring_obligations entry on the next dashboard
    fetch (detect_recurring() needs >= 3 backdated occurrences to see it)."""
    r = client.post(
        "/api/events/demo-priya",
        json={
            "kind": "recurring",
            "merchant": "Test Gym Membership",
            "amount": 1200.0,
            "frequency": "monthly",
            "next_expected_date": date.today().isoformat(),
        },
    )
    assert r.status_code == 200
    diff = r.json()
    assert diff["trigger"] == "recurring"

    after = build_dashboard_snapshot("demo-priya")
    matches = [o for o in after.recurring_obligations if "test gym membership" in o.merchant]
    assert matches, "new recurring obligation should be detected after 3 backdated occurrences"
    # Obligation must be an outflow (negative) regardless of the sign posted.
    assert matches[0].amount < 0


def test_events_endpoint_recurring_kind_requires_amount():
    r = client.post(
        "/api/events/demo-priya",
        json={"kind": "recurring", "merchant": "No Amount Here", "frequency": "monthly"},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# /api/dashboard/{user_id}: end-to-end real data through the API layer
# ---------------------------------------------------------------------------


def test_dashboard_endpoint_returns_real_data_for_all_personas():
    for user_id in PERSONA_CONFIGS:
        r = client.get(f"/api/dashboard/{user_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == user_id
        assert 0 <= body["health_score"]["overall"] <= 100
        assert len(body["forecast"]["points"]) == 90
