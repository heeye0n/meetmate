"""가능 시간 교집합·회의 시간 추천 (순수 Python, LLM 사용 금지).

슬롯 형식: {"member", "day"(MON~SUN), "start"("HH:MM"), "end", "type"(available|unavailable), "evidence"}

팀원별 가능 시간 규칙
- '가능' 시간을 하나라도 말한 사람 → 말한 시간에만 가능
- '불가능' 시간만 말한 사람 → 그 시간을 뺀 나머지 전부 가능
- 아무 말도 없는 사람 → default_available 에 따름
- 같은 칸에 가능/불가능이 겹치면 불가능이 이긴다
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta, timezone

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DAY_KO = {"MON": "월", "TUE": "화", "WED": "수", "THU": "목", "FRI": "금", "SAT": "토", "SUN": "일"}
_KO_TO_DAY = {v: k for k, v in DAY_KO.items()}

DAY_START = 9 * 60   # 09:00
DAY_END = 22 * 60    # 22:00
UNIT = 30            # 30분 칸


# ---------- 시간 변환 ----------
def to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def cell_times(unit: int = UNIT) -> list[str]:
    return [to_hhmm(t) for t in range(DAY_START, DAY_END, unit)]


# ---------- AI 결과 검증 ----------
def _norm_day(value) -> str | None:
    v = str(value or "").strip()
    if v.upper()[:3] in DAYS:
        return v.upper()[:3]
    if v[:1] in _KO_TO_DAY and (len(v) == 1 or v[1:] in ("요일", "욜")):
        return _KO_TO_DAY[v[:1]]
    return None


def _norm_time(value) -> int | None:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(value or ""))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 24 or mi > 59:
        return None
    return h * 60 + mi


def validate_slots(raw: list, members: list[str]) -> tuple[list[dict], list[str]]:
    """AI가 준 슬롯을 검사해 쓸 수 있는 것만 남긴다. (정리된 슬롯, 경고 목록)"""
    slots, warnings = [], []
    for i, item in enumerate(raw or [], 1):
        if not isinstance(item, dict):
            warnings.append(f"{i}번 항목: 형식이 잘못됨")
            continue
        member = str(item.get("member", "")).strip()
        day = _norm_day(item.get("day"))
        start, end = _norm_time(item.get("start")), _norm_time(item.get("end"))
        type_ = str(item.get("type", "available")).strip().lower()
        label = f"{i}번 항목({member or '이름 없음'})"
        if member not in members:
            warnings.append(f"{label}: 팀원 목록에 없는 이름")
            continue
        if day is None:
            warnings.append(f"{label}: 요일을 알 수 없음 ({item.get('day')})")
            continue
        if start is None or end is None:
            warnings.append(f"{label}: 시간 형식 오류")
            continue
        start, end = max(start, DAY_START), min(end, DAY_END)  # 09~22시로 자르기
        if start >= end:
            warnings.append(f"{label}: 시작 시간이 끝 시간보다 늦음")
            continue
        slots.append({
            "member": member, "day": day, "start": to_hhmm(start), "end": to_hhmm(end),
            "type": "unavailable" if type_.startswith("un") else "available",
            "evidence": str(item.get("evidence", "")).strip(),
        })
    return slots, warnings


# ---------- 그리드 ----------
def build_grid(slots: list[dict], members: list[str], unit: int = UNIT, default_available: bool = True) -> dict:
    """{day: [가능한 팀원 frozenset, ...칸별]} 를 만든다."""
    n_cells = (DAY_END - DAY_START) // unit
    grid = {d: [set() for _ in range(n_cells)] for d in DAYS}

    def cells(s):
        a = max(to_min(s["start"]), DAY_START)
        b = min(to_min(s["end"]), DAY_END)
        return range((a - DAY_START) // unit, -(-(b - DAY_START) // unit))  # 끝은 올림

    for m in members:
        mine = [s for s in slots if s["member"] == m]
        avail = [s for s in mine if s["type"] == "available"]
        unavail = [s for s in mine if s["type"] == "unavailable"]
        free = {d: [False] * n_cells for d in DAYS}
        if avail:
            for s in avail:
                for c in cells(s):
                    free[s["day"]][c] = True
        elif unavail or default_available:
            free = {d: [True] * n_cells for d in DAYS}
        for s in unavail:
            for c in cells(s):
                free[s["day"]][c] = False
        for d in DAYS:
            for c in range(n_cells):
                if free[d][c]:
                    grid[d][c].add(m)
    return {d: [frozenset(x) for x in grid[d]] for d in DAYS}


def members_at(grid: dict, day: str, hhmm: str, unit: int = UNIT) -> frozenset:
    return grid[day][(to_min(hhmm) - DAY_START) // unit]


def count_table(grid: dict) -> dict:
    """히트맵용: {day: [가능 인원 수, ...]}"""
    return {d: [len(x) for x in grid[d]] for d in DAYS}


# ---------- 추천 ----------
def _runs(cells_ok: list[bool]) -> list[tuple[int, int]]:
    runs, start = [], None
    for i, ok in enumerate(cells_ok + [False]):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            runs.append((start, i))
            start = None
    return runs


def recommend(grid: dict, members: list[str], duration_minutes: int, top_n: int = 3, unit: int = UNIT) -> list[dict]:
    """전원 가능한 연속 구간 → 부족하면 1명 빠지는 구간 순으로 top_n 개 추천."""
    need = -(-duration_minutes // unit)
    everyone = frozenset(members)
    results = []

    def add_runs(target: frozenset, missing: list[str]):
        for d in DAYS:
            for a, b in _runs([x == target for x in grid[d]]):
                if b - a >= need:
                    s = DAY_START + a * unit
                    results.append({
                        "day": d, "start": to_hhmm(s), "end": to_hhmm(DAY_START + b * unit),
                        "meeting_start": to_hhmm(s), "meeting_end": to_hhmm(s + duration_minutes),
                        "members": [m for m in members if m in target], "missing": missing,
                        "full": not missing, "length": (b - a) * unit,
                    })

    add_runs(everyone, [])
    if len(results) < top_n and len(members) > 1:
        for m in members:
            add_runs(everyone - {m}, [m])

    # 전원 가능 구간: 빠른 요일·시간 순 / 1명 빠지는 구간: 긴 구간 우선
    full = sorted([r for r in results if r["full"]], key=lambda r: (DAYS.index(r["day"]), r["start"]))
    rest = sorted([r for r in results if not r["full"]], key=lambda r: (-r["length"], DAYS.index(r["day"]), r["start"]))
    return (full + rest)[:top_n]


# ---------- 캘린더 ----------
def next_date(day: str, base: date) -> date:
    """base 날짜 이후(당일 포함) 가장 가까운 해당 요일."""
    return base + timedelta(days=(DAYS.index(day) - base.weekday()) % 7)


def to_ics(title: str, day: date, start: str, end: str, description: str = "") -> str:
    def stamp(hhmm):
        return f"{day:%Y%m%d}T{hhmm.replace(':', '')}00"

    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//MeetMate//KO", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uuid.uuid4()}@meetmate",
        f"DTSTAMP:{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
        f"DTSTART:{stamp(start)}",
        f"DTEND:{stamp(end)}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{description}",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
