"""회의록 할 일 정리 (순수 Python): 상대 날짜 계산, 담당자·근거 검증."""
from __future__ import annotations

import re
from datetime import date, timedelta

from core.evidence import evidence_in_source, normalize

WEEKDAYS_KO = "월화수목금토일"
RELATIVE_DAYS = {"오늘": 0, "내일": 1, "모레": 2, "글피": 3}
WEEK_OFFSET = {"이번주": 0, "금주": 0, "다음주": 7, "차주": 7, "다다음주": 14}
PRIORITY = {"높음": "높음", "high": "높음", "보통": "보통", "medium": "보통", "중간": "보통", "낮음": "낮음", "low": "낮음"}
UNASSIGNED = "미정"


def _with_year(month: int, day: int, meeting: date) -> date | None:
    try:
        d = date(meeting.year, month, day)
    except ValueError:
        return None
    # 회의보다 한 달 넘게 이전 날짜면 다음 해로 본다 (12월 회의의 "1/5")
    if d < meeting - timedelta(days=30):
        d = date(meeting.year + 1, month, day)
    return d


def resolve_due(text: str, meeting: date) -> date | None:
    """'금요일까지', '다음 주 월요일', '모레', '12/3' 같은 표현을 회의 날짜 기준 실제 날짜로. 모르면 None(=미정)."""
    t = re.sub(r"\s+", "", text or "")
    t = re.sub(r"(전까지|까지|안에|중으로)$", "", t)
    if not t:
        return None

    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})[/.](\d{1,2})", t) or re.search(r"(\d{1,2})월(\d{1,2})일", t)
    if m:
        return _with_year(int(m.group(1)), int(m.group(2)), meeting)

    for word, delta in RELATIVE_DAYS.items():
        if t.startswith(word):
            return meeting + timedelta(days=delta)

    m = re.search(r"(이번주|금주|다다음주|다음주|차주)?([월화수목금토일])요일", t)
    if m:
        target = WEEKDAYS_KO.index(m.group(2))
        if m.group(1):
            monday = meeting - timedelta(days=meeting.weekday())
            return monday + timedelta(days=WEEK_OFFSET[m.group(1)] + target)
        delta = (target - meeting.weekday()) % 7 or 7  # 회의 당일 요일이면 다음 주
        return meeting + timedelta(days=delta)
    return None


def normalize_actions(raw: list, members: list[str], source: str, meeting: date) -> tuple[list[dict], list[str]]:
    """AI가 준 할 일을 검사한다. 근거에 이름이 없는 담당자는 '미정'으로 바꾼다."""
    actions, warnings = [], []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        task = str(item.get("task", "")).strip()
        if not task:
            warnings.append("내용이 빈 할 일 1개를 뺐어요.")
            continue
        evidence = str(item.get("evidence", "")).strip()
        verified = evidence_in_source(evidence, source)
        assignee = str(item.get("assignee") or "").strip()

        named_in_evidence = assignee in members and assignee in normalize(evidence)
        if not (named_in_evidence and verified):
            if assignee and assignee != UNASSIGNED:
                warnings.append(f"'{task}': 담당자 '{assignee}'가 회의록 근거에 없어서 '미정'으로 바꿨어요.")
            assignee = UNASSIGNED
        if not verified:
            warnings.append(f"'{task}': 근거 문장이 회의록에 없어요. 직접 확인하세요.")

        due_text = str(item.get("due_text") or "").strip()
        due = resolve_due(due_text, meeting)
        actions.append({
            "task": task,
            "assignee": assignee,
            "due": due.isoformat() if due else None,
            "due_text": due_text,
            "priority": PRIORITY.get(str(item.get("priority", "")).strip().lower(), "보통"),
            "evidence": evidence,
            "verified": verified,
        })
    return actions, warnings


def normalize_decisions(raw: list, source: str) -> list[dict]:
    out = []
    for item in raw or []:
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            continue
        evidence = str(item.get("evidence", "")).strip()
        out.append({"text": str(item["text"]).strip(), "evidence": evidence,
                    "verified": evidence_in_source(evidence, source)})
    return out
