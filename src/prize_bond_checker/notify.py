"""Optional Telegram, WhatsApp (Twilio), email, and webhook alerts."""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable
from urllib.parse import urlencode

import requests

from prize_bond_checker.constants import CLAIM_NOTE
from prize_bond_checker.models import Win


@dataclass(frozen=True)
class NotifyResult:
    channel: str
    ok: bool
    detail: str


def configured_channels() -> list[str]:
    channels: list[str] = []
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        channels.append("telegram")
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN") and os.getenv("WHATSAPP_TO"):
        channels.append("whatsapp")
    if os.getenv("SMTP_HOST") and os.getenv("ALERT_EMAIL_TO"):
        channels.append("email")
    if os.getenv("NOTIFY_WEBHOOK_URL"):
        channels.append("webhook")
    return channels


def format_alert(
    outcomes: Iterable[object],
    *,
    include_claim_note: bool = True,
) -> str:
    """Build a plain-text alert from CheckOutcome-like objects."""
    items = list(outcomes)
    if not items:
        return "Prize Bond Checker ran, but there was nothing to report."

    wins: list[tuple[int, str, Win]] = []
    lines = ["Prize Bond Checker"]

    for outcome in items:
        error = getattr(outcome, "error", None)
        skipped = getattr(outcome, "skipped", False)
        denomination = getattr(outcome, "denomination")
        draw = getattr(outcome, "draw", None)
        draw_date = getattr(outcome, "draw_date", None) or (draw.draw_date if draw else "unknown")
        bond_count = getattr(outcome, "bond_count", 0)
        outcome_wins: list[Win] = list(getattr(outcome, "wins", []))

        if error:
            lines.append(f"\nRs. {denomination}: error — {error}")
            continue
        if skipped:
            lines.append(f"\nRs. {denomination} · {draw_date}: already checked, skipped.")
            continue

        meta = [f"Rs. {denomination}", str(draw_date)]
        if draw is not None:
            if draw.draw_number:
                meta.append(f"Draw #{draw.draw_number}")
            if draw.city:
                meta.append(draw.city)
        lines.append(f"\n{' · '.join(meta)}")
        lines.append(f"Checked {bond_count} bond(s).")
        if outcome_wins:
            lines.append(f"{len(outcome_wins)} winning bond(s):")
            for win in outcome_wins:
                owner = f" ({win.owner})" if win.owner else ""
                lines.append(f"  {win.bond}{owner} -> {win.tier} prize ({win.amount})")
                wins.append((denomination, str(draw_date), win))
        else:
            lines.append("No matches this time.")

    if wins:
        lines.insert(1, "\nYOU WON!")
        if include_claim_note:
            lines.append(f"\n{CLAIM_NOTE}")
    else:
        lines.insert(1, "\nNo wins in this run.")

    text = "\n".join(lines).strip()
    return text[:3900]


def send_alerts(text: str) -> list[NotifyResult]:
    results: list[NotifyResult] = []
    channels = configured_channels()
    if not channels:
        return [
            NotifyResult(
                channel="none",
                ok=False,
                detail="No alert channels configured. See .env.example for Telegram, WhatsApp, or email.",
            )
        ]

    if "telegram" in channels:
        results.append(_send_telegram(text))
    if "whatsapp" in channels:
        results.append(_send_whatsapp(text))
    if "email" in channels:
        results.append(_send_email(text))
    if "webhook" in channels:
        results.append(_send_webhook(text))
    return results


def _send_telegram(text: str) -> NotifyResult:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=30,
        )
        response.raise_for_status()
        return NotifyResult("telegram", True, "sent")
    except requests.RequestException as exc:
        return NotifyResult("telegram", False, str(exc))


def _send_whatsapp(text: str) -> NotifyResult:
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    to_number = os.environ["WHATSAPP_TO"]
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        response = requests.post(
            url,
            data=urlencode({"From": from_number, "To": to_number, "Body": text}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(sid, token),
            timeout=30,
        )
        response.raise_for_status()
        return NotifyResult("whatsapp", True, "sent")
    except requests.RequestException as exc:
        return NotifyResult("whatsapp", False, str(exc))


def _send_email(text: str) -> NotifyResult:
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    mail_from = os.getenv("ALERT_EMAIL_FROM") or username
    mail_to = os.environ["ALERT_EMAIL_TO"]
    use_tls = os.getenv("SMTP_TLS", "1") not in {"0", "false", "False"}

    message = EmailMessage()
    message["Subject"] = "Prize Bond Checker"
    message["From"] = mail_from
    message["To"] = mail_to
    message.set_content(text)

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
        return NotifyResult("email", True, "sent")
    except (OSError, smtplib.SMTPException) as exc:
        return NotifyResult("email", False, str(exc))


def _send_webhook(text: str) -> NotifyResult:
    url = os.environ["NOTIFY_WEBHOOK_URL"]
    try:
        response = requests.post(url, json={"text": text}, timeout=30)
        response.raise_for_status()
        return NotifyResult("webhook", True, "sent")
    except requests.RequestException as exc:
        return NotifyResult("webhook", False, str(exc))
