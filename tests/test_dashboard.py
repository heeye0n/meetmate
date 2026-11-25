from datetime import date

from core import dashboard as db

TODAY = date(2026, 11, 26)
MEETINGS = [
    {"id": "m1", "date": "2026-11-25", "title": "1차", "decisions": [{"text": "x"}], "actions": [
        {"task": "DB 정의서", "assignee": "지은", "due": "2026-11-27", "status": "완료"},
        {"task": "API 명세", "assignee": "희연", "due": "2026-11-30", "status": "진행 중"},
        {"task": "UI 시안", "assignee": "도윤", "due": None, "status": "할 일"},
        {"task": "발표 담당 정하기", "assignee": "미정", "due": None, "status": "할 일"},
        {"task": "지난 일", "assignee": "민수", "due": "2026-11-24", "status": "할 일"},
    ]},
    {"id": "m2", "date": "2026-11-26", "title": "2차", "decisions": [], "actions": [
        {"task": "리허설", "assignee": "희연", "due": "2026-11-28", "status": "할 일"},
    ]},
]


def test_summary_numbers():
    s = db.summary(db.flatten(MEETINGS), TODAY)
    assert (s["total"], s["done"], s["in_progress"], s["todo"]) == (6, 1, 1, 4)
    assert s["done_rate"] == 17          # 1/6 → 17%
    assert s["due_soon"] == 1            # 리허설 11/28 (완료된 DB 정의서 11/27 은 제외)
    assert s["overdue"] == 1             # 지난 일 11/24


def test_summary_empty():
    assert db.summary([], TODAY)["done_rate"] == 0


def test_by_member():
    rows = {r["member"]: r for r in db.by_member(db.flatten(MEETINGS))}
    assert rows["희연"]["total"] == 2 and rows["희연"]["done"] == 0
    assert rows["지은"]["done"] == 1
    assert rows["미정"]["total"] == 1


def test_due_list_sorted_with_dday():
    items = db.due_list(db.flatten(MEETINGS), TODAY, days=3)
    assert [i["task"] for i in items] == ["지난 일", "리허설"]
    assert [i["d_day"] for i in items] == [-2, 2]


def test_next_agenda_unassigned_first_and_excludes_done():
    agenda = [i["task"] for i in db.next_agenda(db.flatten(MEETINGS))]
    assert agenda[0] == "발표 담당 정하기"
    assert "DB 정의서" not in agenda
    assert len(agenda) == 5


def test_nearest_deadline():
    assert db.nearest_deadline(db.flatten(MEETINGS), TODAY) == date(2026, 11, 28)
    assert db.nearest_deadline([], TODAY) is None


def test_task_rows_columns_match():
    rows = db.task_rows(db.flatten(MEETINGS))
    assert len(rows) == 6
    assert list(rows[0].keys()) == db.TASK_COLUMNS
    assert rows[2]["마감"] == "미정"
    assert rows[0]["회의"] == "2026-11-25 1차"


def test_meetings_without_actions_give_empty_table_with_columns():
    import pandas as pd

    items = db.flatten([{"id": "m0", "date": "2026-11-26", "title": "킥오프", "actions": []}])
    assert items == []
    table = pd.DataFrame(db.task_rows(items), columns=db.TASK_COLUMNS)
    assert list(table["상태"]) == []  # 컬럼이 있어 KeyError 가 나지 않음
    assert db.summary(items, TODAY)["done_rate"] == 0
    assert db.by_member(items) == [] and db.next_agenda(items) == []
    assert db.nearest_deadline(items, TODAY) is None
