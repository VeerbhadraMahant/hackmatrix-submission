"""Zero-dependency, zero-API-key rule-based router.

This is what keeps FinPilot demoable when the AI is down/rate-limited/unkeyed:
a small keyword/intent classifier that still builds a real AnswerContract out
of the same tool functions used by the online engine (app.copilot.tools) --
it is not canned text, it reflects real snapshot data every time.

`route(user_id, message) -> AnswerContract` is the single entry point.
"""
from __future__ import annotations

import re

from app.copilot import tools
from app.schemas import (
    ActionType,
    AnswerContract,
    DataGap,
    Fact,
    ImpactEstimate,
    Prediction,
    Recommendation,
)

_AMOUNT_RE = re.compile(
    r"(?:₹|rs\.?|inr)\s*([\d][\d,]*(?:\.\d+)?)\s*(k|l|lakh|lakhs|cr|crore)?"
    r"|([\d][\d,]*(?:\.\d+)?)\s*(k|l|lakh|lakhs|cr|crore)?\s*(?:rupees|rs\.?|inr)",
    re.IGNORECASE,
)

_MULTIPLIERS = {
    "k": 1_000,
    "l": 100_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "cr": 10_000_000,
    "crore": 10_000_000,
}


def _extract_amount(message: str) -> float | None:
    match = _AMOUNT_RE.search(message)
    if not match:
        return None
    raw = match.group(1) or match.group(3)
    suffix = (match.group(2) or match.group(4) or "").lower()
    if not raw:
        return None
    try:
        value = float(raw.replace(",", ""))
    except ValueError:
        return None
    return value * _MULTIPLIERS.get(suffix, 1)


def _facts_from_summary(summary: dict) -> list[Fact]:
    if "error" in summary:
        return []
    return [
        Fact(text=f"Net worth is ₹{summary['net_worth']:,.0f}.", value=summary["net_worth"]),
        Fact(
            text=f"Monthly income is ₹{summary['monthly_income']:,.0f} and monthly expenses are ₹{summary['monthly_expenses']:,.0f}.",
            value=summary["monthly_income"] - summary["monthly_expenses"],
        ),
        Fact(
            text=f"Average savings rate is {summary['savings_rate'] * 100:.1f}%.",
            value=summary["savings_rate"],
        ),
        Fact(
            text=f"Overall financial health score is {summary['health_score']:.0f}/100.",
            value=summary["health_score"],
        ),
    ]


def _data_gap_for_error(payload: dict, fallback_text: str) -> DataGap:
    return DataGap(
        text=payload.get("error", fallback_text),
        what_would_help=payload.get("data_gap", "More complete account data."),
    )


def _recommendation_from_snapshot_insights(user_id: str) -> list[Recommendation]:
    """Reuse the demo snapshot's own pre-baked recommendations (which already
    carry real ImpactEstimate objects) as a stand-in until
    forecast-sim-agent's app.recommend.engine lands."""
    summary = tools._snapshot(user_id)
    if summary is None:
        return []
    return list(summary.insights.recommendations)


def _intent_spending(user_id: str, message: str) -> AnswerContract:
    summary = tools.get_summary(user_id)
    recurring = tools.get_recurring(user_id)
    facts = _facts_from_summary(summary)
    data_gaps = []
    if "error" in summary:
        data_gaps.append(_data_gap_for_error(summary, "Could not load spending summary."))
    if "error" not in recurring:
        facts.append(
            Fact(
                text=f"You have {recurring['count']} recurring obligations totalling ₹{recurring['monthly_total']:,.0f}/month.",
                value=recurring["monthly_total"],
            )
        )
    narrative = (
        "Here's how your spending looks based on your latest snapshot."
        if "error" not in summary
        else "I couldn't load your spending summary."
    )
    return AnswerContract(
        query=message,
        facts=facts,
        data_gaps=data_gaps,
        narrative=narrative,
    )


def _intent_savings(user_id: str, message: str) -> AnswerContract:
    summary = tools.get_summary(user_id)
    if "error" in summary:
        return AnswerContract(
            query=message,
            data_gaps=[_data_gap_for_error(summary, "Could not load savings data.")],
            narrative="I couldn't load your savings data.",
        )
    rate = summary["savings_rate"]
    facts = [
        Fact(text=f"Your average monthly savings rate is {rate * 100:.1f}%.", value=rate),
    ]
    predictions = [
        Prediction(
            text="A savings rate below 20% typically leaves little room for a 3-6 month emergency fund.",
            confidence=0.55,
            basis="General personal-finance heuristic (20% rule), not user-specific model output.",
        )
    ]
    recommendations = _recommendation_from_snapshot_insights(user_id)
    narrative = (
        f"You're saving about {rate * 100:.1f}% of income per month."
        + (" That's below a healthy 20% target." if rate < 0.20 else " That's a solid rate.")
    )
    return AnswerContract(
        query=message,
        facts=facts,
        predictions=predictions,
        recommendations=recommendations,
        narrative=narrative,
    )


def _intent_debt(user_id: str, message: str) -> AnswerContract:
    debt = tools.get_debt(user_id)
    if "error" in debt:
        return AnswerContract(
            query=message,
            data_gaps=[_data_gap_for_error(debt, "Could not load debt data.")],
            narrative="I couldn't load your debt data.",
        )
    facts = [
        Fact(
            text=f"You have {debt['count']} debt(s) totalling ₹{debt['total_principal']:,.0f} in principal.",
            value=debt["total_principal"],
        ),
        Fact(
            text=f"Minimum payments across debts total ₹{debt['total_minimum_payment']:,.0f}/month.",
            value=debt["total_minimum_payment"],
        ),
    ]
    data_gaps = []
    if debt.get("debt_to_income_ratio") is not None:
        facts.append(
            Fact(
                text=f"Your debt-to-income ratio is {debt['debt_to_income_ratio'] * 100:.1f}%.",
                value=debt["debt_to_income_ratio"],
            )
        )
    else:
        data_gaps.append(
            DataGap(
                text="Could not compute a debt-to-income ratio.",
                what_would_help=debt.get("data_gap", "Confirmed monthly income."),
            )
        )
    recommendations = [
        r for r in _recommendation_from_snapshot_insights(user_id)
        if r.action in (ActionType.prepay_debt, ActionType.refinance_debt)
    ]
    narrative = "Here's a breakdown of your current debt obligations."
    return AnswerContract(
        query=message,
        facts=facts,
        recommendations=recommendations,
        data_gaps=data_gaps,
        narrative=narrative,
    )


def _intent_cashflow(user_id: str, message: str) -> AnswerContract:
    forecast = tools.get_forecast(user_id, 90)
    if "error" in forecast:
        return AnswerContract(
            query=message,
            data_gaps=[_data_gap_for_error(forecast, "Could not load a cash-flow forecast.")],
            narrative="I couldn't load your cash-flow forecast.",
        )
    facts = [
        Fact(text=f"Forecast basis: {forecast['basis']}"),
    ]
    predictions = []
    if forecast.get("first_gap_date"):
        predictions.append(
            Prediction(
                text=f"Your projected balance may dip below ₹0 around {forecast['first_gap_date']}.",
                confidence=forecast["confidence"],
                basis=forecast["basis"],
            )
        )
        narrative = f"Heads up -- there's a projected cash-flow gap around {forecast['first_gap_date']}."
    else:
        predictions.append(
            Prediction(
                text="No cash-flow gap is projected in the current forecast horizon.",
                confidence=forecast["confidence"],
                basis=forecast["basis"],
            )
        )
        narrative = "Your cash flow looks stable over the forecast horizon -- no projected shortfall."
    return AnswerContract(
        query=message,
        facts=facts,
        predictions=predictions,
        narrative=narrative,
    )


def _intent_affordability(user_id: str, message: str) -> AnswerContract:
    amount = _extract_amount(message)
    if amount is None:
        return AnswerContract(
            query=message,
            data_gaps=[
                DataGap(
                    text="I couldn't find a specific amount in your question.",
                    what_would_help="A rupee amount, e.g. 'Can I afford a ₹60,000 phone?'",
                )
            ],
            narrative="Let me know the amount you're considering and I can check affordability.",
        )
    result = tools.check_affordability(user_id=user_id, amount=amount, description=message)
    if "error" in result:
        return AnswerContract(
            query=message,
            data_gaps=[_data_gap_for_error(result, "Could not run an affordability check.")],
            narrative="I couldn't run an affordability check right now.",
        )
    impact_payload = result.get("impact", {})
    impact = ImpactEstimate(
        metric=impact_payload.get("metric", "monthly free cash flow"),
        before=impact_payload.get("before", 0.0),
        after=impact_payload.get("after", 0.0),
        delta=impact_payload.get("delta", 0.0),
        horizon=impact_payload.get("horizon", "next 3 months"),
    )
    affordable = result.get("affordable")
    facts = [Fact(text=f"You asked about a ₹{amount:,.0f} purchase.", value=amount)]
    if "free_cash_flow_monthly" in result:
        facts.append(
            Fact(
                text=f"Your current monthly free cash flow is ₹{result['free_cash_flow_monthly']:,.0f}.",
                value=result["free_cash_flow_monthly"],
            )
        )
    recommendations = [
        Recommendation(
            action=ActionType.affordability_check,
            text=(
                f"₹{amount:,.0f} looks affordable without disrupting your monthly cash flow."
                if affordable
                else f"₹{amount:,.0f} would strain your monthly cash flow -- consider spreading the cost or waiting."
            ),
            rationale=result.get("note", "Estimated from current monthly free cash flow."),
            impact=impact,
            confidence=result.get("confidence", 0.4),
            action_params={"amount": amount},
        )
    ]
    narrative = (
        f"Based on your current cash flow, a ₹{amount:,.0f} purchase looks "
        + ("affordable." if affordable else "tight -- proceed carefully.")
    )
    return AnswerContract(
        query=message,
        facts=facts,
        recommendations=recommendations,
        narrative=narrative,
    )


def _intent_recommendations(user_id: str, message: str) -> AnswerContract:
    recommendations = _recommendation_from_snapshot_insights(user_id)
    summary = tools.get_summary(user_id)
    facts = _facts_from_summary(summary) if "error" not in summary else []
    if not recommendations:
        return AnswerContract(
            query=message,
            facts=facts,
            data_gaps=[
                DataGap(
                    text="No specific recommendations are available right now.",
                    what_would_help="More transaction history to detect optimization opportunities.",
                )
            ],
            narrative="I don't have a specific recommendation yet -- ask me about debt, subscriptions, or savings.",
        )
    narrative = "Here's what would move the needle most based on your current data."
    return AnswerContract(
        query=message,
        facts=facts,
        recommendations=recommendations,
        narrative=narrative,
    )


def _intent_greeting(user_id: str, message: str) -> AnswerContract:
    return AnswerContract(
        query=message,
        narrative="Hi! I'm your FinPilot copilot. Ask me where your money goes, whether you can afford something, "
        "how to pay off debt faster, or what to invest in next.",
    )


def _intent_fallback(user_id: str, message: str) -> AnswerContract:
    summary = tools.get_summary(user_id)
    if "error" not in summary and not summary.get("monthly_income") and not summary.get("monthly_expenses"):
        return AnswerContract(
            query=message,
            data_gaps=[DataGap(text="No financial data is connected yet.", what_would_help="Connect Google Pay or a bank account on the Connect page.")],
            narrative="I don't see any transactions yet, so there is nothing to analyse. Connect a source and ask me again.",
        )
    facts = _facts_from_summary(summary) if "error" not in summary else []
    recommendations = _recommendation_from_snapshot_insights(user_id)
    return AnswerContract(
        query=message,
        facts=facts,
        recommendations=recommendations,
        data_gaps=[
            DataGap(
                text="I wasn't able to confidently match your question to a specific topic.",
                what_would_help="Try asking about spending, savings, debt, cash flow, affordability, or recommendations.",
            )
        ],
        narrative="Here's a general snapshot of your finances while I work out exactly what you're asking.",
    )


# Ordered (intent_name, keyword_pattern, handler). First match wins.
_INTENTS: list[tuple[str, re.Pattern, callable]] = [
    (
        "greeting",
        re.compile(r"^\s*(hi+|hello+|hey+|namaste|yo|good\s+(morning|afternoon|evening)|thanks?|thank you)\W*$", re.IGNORECASE),
        _intent_greeting,
    ),
    (
        "affordability",
        re.compile(r"\b(afford|should i buy|can i get|can i purchase)\b", re.IGNORECASE),
        _intent_affordability,
    ),
    (
        "debt",
        re.compile(r"\b(debt|credit card|loan|emi)\b", re.IGNORECASE),
        _intent_debt,
    ),
    (
        "cash_flow",
        re.compile(
            r"\b(cash flow|cashflow|run out of money|overdraft|gap|shortfall)\b",
            re.IGNORECASE,
        ),
        _intent_cashflow,
    ),
    (
        "savings",
        re.compile(r"\b(saving|savings rate|save enough|nest egg)\b", re.IGNORECASE),
        _intent_savings,
    ),
    (
        "recommendations",
        re.compile(
            r"\b(what should i do|how can i improve|recommend|recommendation|advice|tips?)\b",
            re.IGNORECASE,
        ),
        _intent_recommendations,
    ),
    (
        "spending",
        re.compile(
            r"\b(how am i doing|spending|expenses|expense|where.*money.*go)\b",
            re.IGNORECASE,
        ),
        _intent_spending,
    ),
]


def classify(message: str) -> str:
    """Return the matched intent name, or 'fallback' if nothing matches."""
    for name, pattern, _handler in _INTENTS:
        if pattern.search(message):
            return name
    return "fallback"


def route(user_id: str, message: str) -> AnswerContract:
    """Classify `message` and produce a real AnswerContract from live tool
    calls against `user_id`'s data. Never raises -- any internal error is
    caught and turned into a minimal, still-valid AnswerContract with a
    DataGap describing the problem."""
    try:
        for name, pattern, handler in _INTENTS:
            if pattern.search(message):
                return handler(user_id, message)
        return _intent_fallback(user_id, message)
    except Exception as exc:  # absolute last resort -- never crash /api/chat
        return AnswerContract(
            query=message,
            data_gaps=[
                DataGap(
                    text=f"Something went wrong answering this offline: {exc}",
                    what_would_help="Retry, or rephrase the question.",
                )
            ],
            narrative="I hit an internal error trying to answer that -- please try again.",
        )
