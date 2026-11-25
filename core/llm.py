"""LLM 호출 모듈.

- 제공자 교체: .env 의 LLM_PROVIDER (openrouter | factchat), LLM_MODEL
- JSON 응답만 받는다: 파싱 실패·네트워크 오류·429/5xx 는 1회 재시도, 그래도 실패하면 LLMError
- 같은 입력은 data/cache/ 에 캐시 (무료 API 한도 절약)
- DEMO_MODE=true 면 API 대신 samples/demo_responses/<demo_key>.json 반환
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
DEMO_DIR = ROOT / "samples" / "demo_responses"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FACTCHAT_URL = "https://factchat-cloud.mindlogic.ai/v1/gateway/claude/v1/messages"
TIMEOUT_SEC = 60
RETRY_WAIT_SEC = 1.5
DEMO_HINT = " 계속 안 되면 .env 에서 DEMO_MODE=true 로 바꿔 오프라인 데모로 시연할 수 있어요."
FORMAT_ERROR = "AI 응답 형식이 예상과 달라요. .env 의 LLM_PROVIDER·LLM_MODEL 설정을 확인하거나 잠시 후 다시 시도하세요."

# 재시도 대기 함수 (테스트에서 monkeypatch 로 바꿔 실제로 기다리지 않게 한다)
_sleep = time.sleep


class LLMError(Exception):
    """사용자에게 그대로 보여줄 수 있는 한국어 오류 메시지를 담는다."""


class RetryableLLMError(LLMError):
    """잠시 후 다시 시도하면 나아질 수 있는 오류 (429, 5xx)."""


def get_config() -> dict:
    """현재 설정을 읽는다. 키 값 자체는 돌려주지 않고 있는지 여부만 알려준다."""
    load_dotenv(ROOT / ".env", override=True)
    provider = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()
    key_name = "FACTCHAT_API_KEY" if provider == "factchat" else "OPENROUTER_API_KEY"
    return {
        "provider": provider,
        "model": os.getenv("LLM_MODEL", "").strip(),
        "demo_mode": os.getenv("DEMO_MODE", "false").strip().lower() == "true",
        "key_name": key_name,
        "has_key": bool(os.getenv(key_name, "").strip()),
    }


def extract_json(text: str) -> dict:
    """응답 문자열에서 JSON 객체를 꺼낸다. 코드 블록(```json)이나 앞뒤 설명이 섞여 있어도 처리."""
    if not text:
        raise ValueError("빈 응답")
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("JSON 객체를 찾지 못함")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON 객체가 아님")
    return data


def _cache_path(cfg: dict, system_prompt: str, user_text: str) -> Path:
    raw = json.dumps([cfg["provider"], cfg["model"], system_prompt, user_text], ensure_ascii=False)
    return CACHE_DIR / (hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32] + ".json")


def _call_openrouter(model: str, key: str, system_prompt: str, user_text: str) -> str:
    resp = requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
        },
        timeout=TIMEOUT_SEC,
    )
    _raise_for_status(resp)
    # 200 이어도 {"error":...}, choices: [], HTML 본문 등이 올 수 있다
    try:
        content = resp.json()["choices"][0]["message"]["content"]
        if content is not None and not isinstance(content, str):
            raise TypeError("content 가 문자열이 아님")
        return content or ""
    except (KeyError, IndexError, TypeError, ValueError):
        raise LLMError(FORMAT_ERROR) from None


def _call_factchat(model: str, key: str, system_prompt: str, user_text: str) -> str:
    # 강의 안내: urllib 은 403(1010)으로 막히므로 requests + user-agent 사용, max_tokens 1024 이상
    resp = requests.post(
        FACTCHAT_URL,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {key}",
            "anthropic-version": "2023-06-01",
            "user-agent": "claude-cli/2.0.0 (external, cli)",
        },
        json={
            "model": model,
            "max_tokens": 2048,
            "temperature": 0,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_text}],
        },
        timeout=TIMEOUT_SEC,
    )
    _raise_for_status(resp)
    try:
        blocks = resp.json()["content"]
        if not isinstance(blocks, list) or not all(isinstance(b, dict) for b in blocks):
            raise TypeError("content 블록 형식이 다름")
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except (KeyError, IndexError, TypeError, ValueError):
        raise LLMError(FORMAT_ERROR) from None


def _raise_for_status(resp: requests.Response) -> None:
    if resp.ok:
        return
    code = resp.status_code
    if code in (401, 403):
        raise LLMError(f"API 키가 올바르지 않거나 접근이 막혔어요 (HTTP {code}). .env 의 키를 확인하세요.")
    if code == 404:
        raise LLMError(f"모델을 찾을 수 없어요 (HTTP 404). .env 의 LLM_MODEL 이름을 확인하세요.")
    if code == 429:
        raise RetryableLLMError("요청 한도를 넘었어요 (HTTP 429). 잠시 후 다시 시도하세요.")
    if code >= 500:
        raise RetryableLLMError(f"AI 서버 오류가 났어요 (HTTP {code}). 잠시 후 다시 시도하세요.")
    # 그 밖의 4xx 는 다시 보내도 같은 결과라 재시도하지 않는다
    raise LLMError(f"AI 요청이 거절됐어요 (HTTP {code}). .env 의 LLM_PROVIDER·LLM_MODEL 설정을 확인하세요.")


def ask_json(system_prompt: str, user_text: str, *, demo_key: str | None = None, use_cache: bool = True) -> dict:
    """LLM 에 질문하고 JSON(dict)으로 답을 받는다. 실패하면 LLMError."""
    cfg = get_config()

    if cfg["demo_mode"]:
        if not demo_key:
            raise LLMError("데모 모드에서는 샘플 데이터만 분석할 수 있어요. 직접 입력한 내용을 분석하려면 .env 에 API 키를 넣고 DEMO_MODE=false 로 바꾸세요.")
        path = DEMO_DIR / f"{demo_key}.json"
        if not path.exists():
            raise LLMError(f"데모 응답 파일이 없어요: samples/demo_responses/{demo_key}.json")
        return json.loads(path.read_text(encoding="utf-8"))

    if cfg["provider"] not in ("openrouter", "factchat"):
        raise LLMError(f"LLM_PROVIDER 는 openrouter 또는 factchat 이어야 해요 (현재: {cfg['provider']}).")
    if not cfg["model"]:
        raise LLMError(".env 에 LLM_MODEL 이 비어 있어요.")
    if not cfg["has_key"]:
        raise LLMError(f".env 에 {cfg['key_name']} 이 비어 있어요. 키를 넣거나 DEMO_MODE=true 로 바꾸세요.")

    cache = _cache_path(cfg, system_prompt, user_text)
    if use_cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    key = os.getenv(cfg["key_name"], "").strip()
    call = _call_factchat if cfg["provider"] == "factchat" else _call_openrouter
    system = system_prompt + "\n\n반드시 JSON 객체 하나만 출력하라. 설명 문장이나 코드 블록 없이."

    last_error: LLMError | None = None
    json_retry = False
    for attempt in range(2):
        if json_retry:
            user = user_text + "\n\n(이전 응답이 올바른 JSON이 아니었다. JSON 객체만 다시 출력하라.)"
        else:
            user = user_text
        try:
            text = call(cfg["model"], key, system, user)
        except requests.Timeout:
            last_error = LLMError(f"AI 응답이 {TIMEOUT_SEC}초 안에 오지 않았어요. 다시 시도하세요.")
        except requests.ConnectionError:
            last_error = LLMError("AI 서버에 연결하지 못했어요. 인터넷 연결을 확인하세요.")
        except requests.RequestException:
            last_error = LLMError("AI 서버와 통신하는 중 오류가 났어요. 잠시 후 다시 시도하세요.")
        except RetryableLLMError as e:
            last_error = e
        except LLMError as e:
            # 401/403/404, 응답 형식 오류 등은 다시 보내도 같으므로 바로 안내
            raise LLMError(f"{e}{DEMO_HINT}") from None
        else:
            try:
                data = extract_json(text)
            except ValueError as e:  # json.JSONDecodeError 포함
                last_error = LLMError(f"AI 응답을 JSON으로 읽지 못했어요 ({e}). 다시 시도하거나 모델을 바꿔 보세요.")
                json_retry = True
                continue
            if use_cache:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        # 네트워크·429·5xx: 잠깐 기다렸다가 1회 재시도
        if attempt == 0:
            _sleep(RETRY_WAIT_SEC)

    raise LLMError(f"{last_error}{DEMO_HINT}") from None
