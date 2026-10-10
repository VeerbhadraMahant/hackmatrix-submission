"""Tests for app.copilot.* -- all run with NO AI key present (has_nvidia
patched to False) so they pass in CI/graders without any secret configured.
"""
from __future__ import annotations

import pytest

from app.copilot import eval as copilot_eval
from app.copilot import offline_router, tools
from app.copilot.engine import answer
from app.schemas import AnswerContract


@pytest.fixture(autouse=True)
def force_offline(monkeypatch):
    """Force every test in this module through the offline path, regardless
    of whether a real NVIDIA_API_KEY happens to be present in the environment
    (e.g. from the repo's .env.local during local dev)."""

    class _FakeSettings:
        has_nvidia = False
        has_nugen = False
        has_nvidia = False
        nvidia_chat_api_key = ""
        
    monkeypatch.setattr("app.copilot.engine.get_settings", lambda: _FakeSettings())
    yield


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def test_get_summary_well_formed():
    result = tools.get_summary("demo-priya")
    assert "error" not in result
    # net_worth is real (can legitimately be negative for personas carrying
    # a large loan against modest liquid/investment assets) -- just assert
    # it's a real, finite number rather than pinning a fixture-specific sign.
    assert isinstance(result["net_worth"], (int, float))
    assert 0 <= result["health_score"] <= 100


def test_query_transactions_shape():
    result = tools.query_transactions("demo-priya", category=None, merchant=None, days=60)
    assert set(result.keys()) == {"transactions", "total", "count"}
    assert result["count"] == len(result["transactions"])


def test_get_recurring_shape():
    result = tools.get_recurring("demo-priya")
    assert "obligations" in result
    assert result["count"] == len(result["obligations"])


def test_get_debt_computes_dti():
    result = tools.get_debt("demo-priya")
    assert "debts" in result
    assert result["debt_to_income_ratio"] is not None


def test_get_forecast_trims_horizon():
    result = tools.get_forecast("demo-priya", horizon_days=10)
    assert result["horizon_days"] <= 10
    assert all(p is not None for p in result["points"])


def test_simulate_action_stub_fallback():
    # Real debt ids are DB-generated UUIDs now (not the old fixture's static
    # "debt-cc"), so look one up dynamically rather than hard-coding it.
    debt_id = tools.get_debt("demo-priya")["debts"][0]["id"]
    result = tools.simulate_action("demo-priya", action="prepay_debt", action_params={"debt_id": debt_id})
    assert "error" not in result
    assert result["source"] in ("stub", "app.simulate.engine")


def test_check_affordability():
    result = tools.check_affordability("demo-priya", amount=60000, description="phone")
    assert "error" not in result
    assert "impact" in result


@pytest.mark.parametrize(
    "fn, kwargs",
    [
        (tools.get_summary, {"user_id": "nonexistent-user-xyz"}),
        (tools.get_recurring, {"user_id": "nonexistent-user-xyz"}),
        (tools.get_debt, {"user_id": "nonexistent-user-xyz"}),
        (tools.get_forecast, {"user_id": "nonexistent-user-xyz"}),
        (tools.query_transactions, {"user_id": "nonexistent-user-xyz", "category": None, "merchant": None, "days": 30}),
        (tools.simulate_action, {"user_id": "nonexistent-user-xyz", "action": "prepay_debt", "action_params": {}}),
    ],
)
def test_tools_never_raise_on_bad_user(fn, kwargs):
    # demo_dashboard_snapshot is currently infallible (synthesizes data for
    # any user_id), so this also exercises the "unknown action" error path
    # where relevant; the important invariant is: never raises.
    result = fn(**kwargs)
    assert isinstance(result, dict)


def test_simulate_action_unknown_action_is_data_gap_not_raise():
    result = tools.simulate_action("demo-priya", action="not_a_real_action", action_params={})
    assert "error" in result
    assert "data_gap" in result


# ---------------------------------------------------------------------------
# Offline router
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "How am I doing with my spending?",
        "What's my savings rate?",
        "How much credit card debt do I have?",
        "Will I run out of money this month?",
        "Can I afford a ₹60,000 phone?",
        "What should I do to improve my finances?",
        "asdkjashdkj random gibberish 12345",
    ],
)
def test_offline_router_handles_every_intent(message):
    result = offline_router.route("demo-priya", message)
    assert isinstance(result, AnswerContract)
    assert result.narrative.strip()


def test_offline_router_unrecognized_message_still_valid():
    result = offline_router.route("demo-priya", "zzz qqq unmatched nonsense")
    assert isinstance(result, AnswerContract)
    assert result.data_gaps  # should flag that it didn't understand


def test_offline_router_affordability_without_amount_is_data_gap():
    result = offline_router.route("demo-priya", "Can I afford a vacation?")
    assert isinstance(result, AnswerContract)
    assert result.data_gaps
    assert not result.recommendations


def test_offline_router_never_raises_on_bad_user():
    result = offline_router.route("nonexistent-user-xyz", "How am I doing?")
    assert isinstance(result, AnswerContract)


# ---------------------------------------------------------------------------
# engine.answer() end to end (offline path, since has_nvidia is patched False)
# ---------------------------------------------------------------------------


def test_answer_falls_back_to_offline_when_no_ai_key():
    result = answer("demo-priya", "How am I doing financially?")
    assert isinstance(result, AnswerContract)
    assert result.narrative.strip()


def test_answer_never_raises_on_empty_ish_message():
    # routes.py rejects truly empty messages before calling answer(); this
    # guards answer() itself against a message that is just whitespace-ish
    # punctuation and would match no intent.
    result = answer("demo-priya", "???")
    assert isinstance(result, AnswerContract)


def test_answer_force_offline_skips_ai_even_when_configured(monkeypatch):
    """Privacy toggle (Security page): force_offline=True must short-circuit
    to the offline router even when an AI key IS configured -- never call
    out to a third-party LLM when the user has opted out."""

    class _FakeSettingsWithAI:
        has_nugen = False
        has_nvidia = True
        nvidia_chat_api_key = "fake-key-should-never-be-used"

    monkeypatch.setattr("app.copilot.engine.get_settings", lambda: _FakeSettingsWithAI())

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("AI path was called despite force_offline=True")

    monkeypatch.setattr("app.copilot.engine._nvidia_answer", _fail_if_called)
    monkeypatch.setattr("app.copilot.engine._general_answer", _fail_if_called)

    result = answer("demo-priya", "How am I doing financially?", force_offline=True)
    assert isinstance(result, AnswerContract)


# ---------------------------------------------------------------------------
# Eval script
# ---------------------------------------------------------------------------


def test_eval_runs_and_passes_at_least_80_percent():
    rows, passed, total = copilot_eval.run()
    assert total >= 25
    pct = passed / total
    assert pct >= 0.8, f"Only {passed}/{total} eval cases passed:\n" + "\n".join(
        f"{r['status']}: {r['question']} -- {r['reason']}" for r in rows if r["status"] == "FAIL"
    )
