from qismat.models import DrawResult, Win
from qismat.notify import configured_channels, format_alert, send_alerts
from qismat.service import CheckOutcome


def test_configured_channels(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("NOTIFY_WEBHOOK_URL", raising=False)
    assert configured_channels() == []

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert configured_channels() == ["telegram"]


def test_format_alert_includes_wins():
    draw = DrawResult(denomination=200, draw_date="2026-03-16", city="Karachi")
    outcome = CheckOutcome(
        denomination=200,
        bond_count=3,
        draw_date="2026-03-16",
        draw=draw,
        wins=[Win(bond="022667", tier="3rd", amount="Rs. 1,250", owner="ali")],
    )
    text = format_alert([outcome])
    assert "YOU WON" in text
    assert "022667" in text
    assert "ali" in text
    assert "National Savings" in text


def test_send_alerts_without_channels(monkeypatch):
    for key in (
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "WHATSAPP_TO",
        "SMTP_HOST",
        "ALERT_EMAIL_TO",
        "NOTIFY_WEBHOOK_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    results = send_alerts("hello")
    assert results[0].channel == "none"
    assert results[0].ok is False


def test_send_telegram(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "99")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("NOTIFY_WEBHOOK_URL", raising=False)

    class FakeResponse:
        def raise_for_status(self):
            return None

    captured = {}

    def fake_post(url, json=None, timeout=0, **kwargs):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr("qismat.notify.requests.post", fake_post)
    results = send_alerts("hello family")
    assert results == [type(results[0])("telegram", True, "sent")] or results[0].ok
    assert results[0].ok is True
    assert "sendMessage" in captured["url"]
    assert captured["json"]["text"] == "hello family"
