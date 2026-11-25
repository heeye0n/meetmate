import json

import pytest
import requests

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


# ---------- 응답 형식 오류 · 재시도 (requests.post 를 가짜로 바꿔 실제 호출 없음) ----------

def _response(status: int, body) -> requests.Response:
    """가짜 HTTP 응답. body 가 str 이면 그대로, 아니면 JSON 으로 담는다."""
    resp = requests.Response()
    resp.status_code = status
    resp._content = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
    return resp


def _ok(content: str) -> requests.Response:
    return _response(200, {"choices": [{"message": {"content": content}}]})


@pytest.fixture
def fake_api(monkeypatch, tmp_path):
    """설정·캐시·대기를 테스트용으로 바꾸고, 응답 목록을 차례로 돌려주는 requests.post 를 심는다."""
    def setup(responses, provider="openrouter"):
        key_name = "FACTCHAT_API_KEY" if provider == "factchat" else "OPENROUTER_API_KEY"
        monkeypatch.setattr(llm, "get_config", lambda: {
            "demo_mode": False, "provider": provider, "model": "test-model",
            "key_name": key_name, "has_key": True,
        })
        monkeypatch.setenv(key_name, "test-key")
        monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
        waits = []
        monkeypatch.setattr(llm, "_sleep", waits.append)
        calls = []
        queue = list(responses)

        def fake_post(*args, **kwargs):
            calls.append(kwargs)
            item = queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        monkeypatch.setattr(llm.requests, "post", fake_post)
        return calls, waits
    return setup


@pytest.mark.parametrize("body", [
    {"error": {"message": "provider down"}},
    {"choices": []},
    "<html><body>Bad Gateway</body></html>",
])
def test_bad_format_200_gives_llm_error(fake_api, body):
    calls, _ = fake_api([_response(200, body)])
    with pytest.raises(llm.LLMError, match="형식이 예상과 달라요") as e:
        llm.ask_json("sys", "user", use_cache=False)
    assert "DEMO_MODE=true" in str(e.value)
    assert "provider down" not in str(e.value) and "html" not in str(e.value)  # 응답 본문은 노출하지 않음
    assert "test-key" not in str(e.value)
    assert len(calls) == 1


@pytest.mark.parametrize("body", [
    {"error": {"message": "x"}},
    {"content": "문자열"},
    {"content": ["블록이 dict 가 아님"]},
    "not json",
])
def test_factchat_bad_format_gives_llm_error(fake_api, body):
    fake_api([_response(200, body)], provider="factchat")
    with pytest.raises(llm.LLMError, match="형식이 예상과 달라요"):
        llm.ask_json("sys", "user", use_cache=False)


def test_timeout_once_then_success_retries(fake_api):
    calls, waits = fake_api([requests.Timeout(), _ok('{"ok": true}')])
    assert llm.ask_json("sys", "user", use_cache=False) == {"ok": True}
    assert len(calls) == 2
    assert waits == [llm.RETRY_WAIT_SEC]


def test_connection_error_twice_gives_llm_error(fake_api):
    calls, _ = fake_api([requests.ConnectionError(), requests.ConnectionError()])
    with pytest.raises(llm.LLMError, match="DEMO_MODE=true"):
        llm.ask_json("sys", "user", use_cache=False)
    assert len(calls) == 2


def test_other_request_exception_gives_llm_error(fake_api):
    fake_api([requests.RequestException(), requests.RequestException()])
    with pytest.raises(llm.LLMError, match="DEMO_MODE=true"):
        llm.ask_json("sys", "user", use_cache=False)


def test_429_twice_gives_llm_error_with_demo_hint(fake_api):
    calls, waits = fake_api([_response(429, {}), _response(429, {})])
    with pytest.raises(llm.LLMError, match="429") as e:
        llm.ask_json("sys", "user", use_cache=False)
    assert "DEMO_MODE=true" in str(e.value)
    assert len(calls) == 2
    assert len(waits) == 1


def test_500_once_then_success_retries(fake_api):
    calls, _ = fake_api([_response(503, "down"), _ok('{"ok": 1}')])
    assert llm.ask_json("sys", "user", use_cache=False) == {"ok": 1}
    assert len(calls) == 2


@pytest.mark.parametrize("status", [401, 403, 404])
def test_auth_or_not_found_does_not_retry(fake_api, status):
    calls, waits = fake_api([_response(status, {}), _ok('{"ok": true}')])
    with pytest.raises(llm.LLMError, match=str(status)) as e:
        llm.ask_json("sys", "user", use_cache=False)
    assert "DEMO_MODE=true" in str(e.value)
    assert len(calls) == 1
    assert waits == []


def test_invalid_json_text_retries_with_hint(fake_api):
    calls, waits = fake_api([_ok("JSON 아님"), _ok('{"ok": true}')])
    assert llm.ask_json("sys", "user", use_cache=False) == {"ok": True}
    assert "JSON 객체만 다시 출력하라" in calls[1]["json"]["messages"][1]["content"]
    assert waits == []  # JSON 재요청은 기다리지 않음
