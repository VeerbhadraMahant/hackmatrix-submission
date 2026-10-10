"""Optional cash-flow gap alert email.

This is a nice-to-have, explicitly-triggered notification (NOT wired to fire
automatically on every dashboard/forecast request -- that would spam users).
The API exposes it behind `POST /api/alerts/gap/{user_id}` so the frontend
can put it behind an explicit button ("email me if this happens").
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from app.core.config import get_settings
from app.schemas import CashFlowForecast

logger = logging.getLogger(__name__)

_GAP_ALERT_WINDOW_DAYS = 14


def maybe_send_gap_alert(user_email: str, forecast: CashFlowForecast) -> bool:
    """Send a cash-flow gap warning email if conditions are met.

    Returns True if an email was actually sent, False otherwise (including
    on any failure -- this function must never raise).
    """
    try:
        settings = get_settings()
        if not settings.has_resend:
            logger.info("gap alert skipped: Resend not configured")
            return False

        if not forecast.first_gap_date:
            return False

        days_until_gap = (forecast.first_gap_date - datetime.now(timezone.utc).date()).days
        if days_until_gap < 0 or days_until_gap > _GAP_ALERT_WINDOW_DAYS:
            return False

        if not user_email:
            logger.warning("gap alert skipped: no recipient email")
            return False

        import resend

        resend.api_key = settings.resend_api_key

        gap_date: date = forecast.first_gap_date
        subject = f"FinPilot: possible cash-flow gap around {gap_date.isoformat()}"
        html = (
            f"<p>Heads up -- based on your current recurring obligations and "
            f"spending pattern, your projected balance may dip below zero "
            f"around <strong>{gap_date.isoformat()}</strong> "
            f"(in {days_until_gap} day(s)).</p>"
            f"<p>Forecast confidence: {forecast.confidence:.0%}. {forecast.basis}</p>"
            f"<p>Open FinPilot to see options to avoid this (e.g. shifting a "
            f"payment date, reducing spend, or building a buffer).</p>"
        )

        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [user_email],
                "subject": subject,
                "html": html,
            }
        )
        return True
    except Exception:  # noqa: BLE001 -- alerts must never break the caller
        logger.exception("Failed to send cash-flow gap alert email")
        return False
