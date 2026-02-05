from typing import List
from sqlalchemy.orm import Session

from app.db.models.alerts import AlertEvent
from app.core.config import settings
from app.services.email_service import send_email


def notify_admin_for_real_alerts(
    db: Session,
    alerts: List[AlertEvent],
):
    """
    Send ONE summary email for newly created REAL alerts.
    """

    if not alerts:
        return

    # Group alerts by severity
    grouped: dict[str, list[AlertEvent]] = {}
    for alert in alerts:
        grouped.setdefault(alert.severity, []).append(alert)

    # Build email text
    lines: list[str] = []
    lines.append("🚨 PlatformOPS – REAL Alerts Detected")
    lines.append("")
    lines.append(f"Total new alerts: {len(alerts)}")
    lines.append("")

    for severity, items in grouped.items():
        lines.append(f"Severity: {severity.upper()} ({len(items)})")
        for a in items:
            lines.append(
                f"- Component: {a.component_code} | "
                f"Signal: {a.signal_code} | "
                f"Ticks: {a.tick_start} → {a.tick_end} | "
                f"Peak: {a.peak_value}"
            )
        lines.append("")

    body = "\n".join(lines)

    send_email(
        to_email=settings.SMTP_FROM_EMAIL,  # admin inbox (MailHog)
        subject="🚨 PlatformOPS – Alert Summary",
        text=body,
    )
