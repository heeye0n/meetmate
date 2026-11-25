"""대시보드 숫자 계산 (순수 Python)."""
from __future__ import annotations

from datetime import date

DONE = "완료"
UNASSIGNED = "미정"


def flatten(meetings: list[dict]) -> list[dict]:
    """회의별 할 일을 한 줄씩 펼친다. 상태 변경용으로 meeting_id·index 를 함께 담는다."""
    items = []
    for m in meetings:
        for i, a in enumerate(m.get("actions", [])):
            items.append({**a, "status": a.get("status", "할 일"), "meeting_id": m.get("id"), "index": i,
                          "meeting_date": m.get("date", ""), "meeting_title": m.get("title", "")})
    return items


def _due(item) -> date | None:
    try:
        return date.fromisoformat(item["due"]) if item.get("due") else None
    except ValueError:
        return None


def summary(items: list[dict], today: date, days: int = 3) -> dict:
    total = len(items)
    done = sum(i["status"] == DONE for i in items)
    open_items = [i for i in items if i["status"] != DONE and _due(i)]
    return {
        "total": total,
        "done": done,
        "in_progress": sum(i["status"] == "진행 중" for i in items),
        "todo": sum(i["status"] == "할 일" for i in items),
        "done_rate": round(done * 100 / total) if total else 0,
        "due_soon": sum(0 <= (_due(i) - today).days <= days for i in open_items),
        "overdue": sum((_due(i) - today).days < 0 for i in open_items),
    }


def by_member(items: list[dict]) -> list[dict]:
    rows: dict[str, dict] = {}
    for i in items:
        r = rows.setdefault(i.get("assignee") or UNASSIGNED, {"member": i.get("assignee") or UNASSIGNED, "total": 0, "done": 0})
        r["total"] += 1
        r["done"] += i["status"] == DONE
    # 미정은 맨 뒤
    return sorted(rows.values(), key=lambda r: (r["member"] == UNASSIGNED, r["member"]))


def due_list(items: list[dict], today: date, days: int = 3) -> list[dict]:
    """지난 마감 + days 일 안에 마감인 미완료 할 일 (D-day 오름차순)."""
    out = []
    for i in items:
        d = _due(i)
        if i["status"] != DONE and d and (d - today).days <= days:
            out.append({**i, "d_day": (d - today).days})
    return sorted(out, key=lambda i: i["d_day"])


def next_agenda(items: list[dict]) -> list[dict]:
    """다음 회의 안건: 미완료 할 일. 담당 미정 → 마감 빠른 순 → 마감 없음."""
    open_items = [i for i in items if i["status"] != DONE]
    return sorted(open_items, key=lambda i: (i.get("assignee") != UNASSIGNED, _due(i) is None, _due(i) or date.max))


def nearest_deadline(items: list[dict], today: date) -> date | None:
    dues = [_due(i) for i in items if i["status"] != DONE and _due(i) and _due(i) >= today]
    return min(dues) if dues else None
