"""Goal progress projection.

Kept pure (no I/O, no DB) so forecast-sim-agent's simulate engine can call
`project_goal` directly with a hypothetical `monthly_contribution` (e.g.
"if this recommendation frees up ₹X/month, does the goal land on time?").
"""
from __future__ import annotations

import math
from datetime import date

import pandas as pd

from app.schemas import Goal


def _add_months(start: date, months: int) -> date:
    return (pd.Timestamp(start) + pd.DateOffset(months=months)).date()


def project_goal(goal: Goal, monthly_contribution: float) -> dict:
    """Project when `goal` will be reached at `monthly_contribution` INR/month.

    Returns:
        projected_completion_date: date | None (None if contribution <= 0 and
            the goal isn't already met)
        on_track: bool (True if no target_date is set, or projected date is
            on/before it)
        months_remaining: int (0 if already met)
    """
    remaining = max(0.0, goal.target_amount - goal.current_amount)
    today = date.today()

    if remaining <= 0:
        return {
            "projected_completion_date": today,
            "on_track": True,
            "months_remaining": 0,
        }

    if monthly_contribution <= 0:
        return {
            "projected_completion_date": None,
            "on_track": False,
            "months_remaining": None,
        }

    months_remaining = math.ceil(remaining / monthly_contribution)
    projected_completion_date = _add_months(today, months_remaining)

    on_track = goal.target_date is None or projected_completion_date <= goal.target_date

    return {
        "projected_completion_date": projected_completion_date,
        "on_track": on_track,
        "months_remaining": months_remaining,
    }
