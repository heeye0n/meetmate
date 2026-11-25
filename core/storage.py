"""회의 이력과 팀원-GitHub 아이디 연결을 로컬 JSON(data/)에 저장한다. data/ 는 gitignore."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.llm import ROOT

DATA_DIR = ROOT / "data"
STATUSES = ["할 일", "진행 중", "완료"]


def _path(name: str) -> Path:
    return DATA_DIR / name


def _read(name: str, default):
    p = _path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write(name: str, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path(name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_path(name))  # 쓰다가 꺼져도 기존 파일이 깨지지 않게


# ---------- 회의 ----------
def load_meetings() -> list[dict]:
    return _read("meetings.json", [])


def save_meeting(meeting: dict) -> str:
    meetings = load_meetings()
    meeting = dict(meeting)
    meeting.setdefault("id", datetime.now().strftime("%Y%m%d%H%M%S%f"))
    meeting["saved_at"] = datetime.now().isoformat(timespec="seconds")
    meeting["actions"] = [{**a, "status": a.get("status", "할 일")} for a in meeting.get("actions", [])]
    meetings = [m for m in meetings if m.get("id") != meeting["id"]] + [meeting]
    meetings.sort(key=lambda m: (m.get("date", ""), m.get("saved_at", "")))
    _write("meetings.json", meetings)
    return meeting["id"]


def update_action(meeting_id: str, index: int, **fields) -> bool:
    meetings = load_meetings()
    for m in meetings:
        if m.get("id") == meeting_id and 0 <= index < len(m.get("actions", [])):
            m["actions"][index].update(fields)
            _write("meetings.json", meetings)
            return True
    return False


def delete_meeting(meeting_id: str) -> None:
    _write("meetings.json", [m for m in load_meetings() if m.get("id") != meeting_id])


# ---------- 팀원 → GitHub 아이디 ----------
def load_members() -> dict:
    return _read("members.json", {})


def save_members(mapping: dict) -> None:
    _write("members.json", {k: v for k, v in mapping.items() if k and v})
