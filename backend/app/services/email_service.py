"""Email-Benachrichtigung ans Team nach einem Onboarding-Lauf - direkt per
SMTP, kein n8n/Webhook-Umweg."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings


def send_onboarding_notification(data: dict, drive_link: str, github_link: str, activated_steps: list[str]) -> None:
    settings = get_settings()

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_user
    msg["To"] = settings.notification_email
    msg["Subject"] = f"Neues Onboarding: {data.get('kundenname', '')}"

    body = f"""Ein neues Onboarding wurde gestartet.

Kunde:        {data.get('kundenname', '')}
Projekttyp:   {data.get('projekttyp', '')}
Setup:        {data.get('setup_preis', '')}€ einmalig + {data.get('monatliche_rate', '')}€/Monat
Projektstart: {data.get('projektstart_datum', '')}

Drive-Ordner: {drive_link or '-'}
GitHub-Repo:  {github_link or '-'}

Aktivierte Schritte: {', '.join(activated_steps)}
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
