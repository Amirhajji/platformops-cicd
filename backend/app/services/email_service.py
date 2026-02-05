# app/services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings


def send_email(
    to_email: str,
    subject: str,
    text: str,
    html: str | None = None,
):
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(text, "plain"))

    if html:
        msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.sendmail(
            settings.SMTP_FROM_EMAIL,
            [to_email],
            msg.as_string(),
        )
