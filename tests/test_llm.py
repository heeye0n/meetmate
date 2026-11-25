import pytest

from core import llm


def test_extract_json_plain():
    assert llm.extract_json('{"ok": true}') == {"ok": True}


def test_extract_json_code_block_with_text():
    text = '알겠습니다.\n```json\n{"a": 1, "b": "한글"}\n```\n끝.'
    assert llm.extract_json(text) == {"a": 1, "b": "한글"}


def test_extract_json_invalid():
    with pytest.raises(ValueError):
        llm.extract_json("JSON이 없는 응답")


def test_demo_mode_returns_saved_response(monkeypatch):
    monkeypatch.setattr(llm, "get_config", lambda: {"demo_mode": True})
    data = llm.ask_json("sys", "user", demo_key="connection_test")
    assert data["ok"] is True


def test_missing_key_gives_friendly_error(monkeypatch):
    monkeypatch.setattr(
        llm,
        "get_config",
        lambda: {"demo_mode": False, "provider": "openrouter", "model": "x", "key_name": "OPENROUTER_API_KEY", "has_key": False},
    )
    with pytest.raises(llm.LLMError, match="OPENROUTER_API_KEY"):
        llm.ask_json("sys", "user")
