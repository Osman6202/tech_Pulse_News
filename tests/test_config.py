import os
import importlib


def test_validate_config_warns_on_placeholder_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "your-telegram-bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
    import config
    importlib.reload(config)
    warnings = config.validate_config()
    assert any("TELEGRAM_BOT_TOKEN" in w for w in warnings)


def test_validate_config_warns_on_empty_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "real-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "your-telegram-chat-id")
    import config
    importlib.reload(config)
    warnings = config.validate_config()
    assert any("TELEGRAM_CHAT_ID" in w for w in warnings)


def test_validate_config_returns_empty_when_valid(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "real-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654")
    import config
    importlib.reload(config)
    warnings = config.validate_config()
    assert warnings == []
