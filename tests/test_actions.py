from datetime import date

import pytest

from core import actions as ac

MEETING = date(2026, 11, 25)  # 수요일
MEMBERS = ["민수", "지은", "희연", "도윤"]
SOURCE = """지은이 DB 테이블 정의서를 금요일까지 수정하기로 함.
희연은 API 명세서를 다음 주 월요일까지 정리해서 노션에 올리기로 함.
발표 자료는 누가 할지 아직 못 정함."""


@pytest.mark.parametrize("text, expected", [
    ("금요일까지", date(2026, 11, 27)),
    ("다음 주 월요일까지", date(2026, 11, 30)),
    ("다음주 금요일", date(2026, 12, 4)),
    ("이번 주 일요일", date(2026, 11, 29)),
    ("수요일", date(2026, 12, 2)),          # 회의 당일 요일이면 다음 주
    ("모레", date(2026, 11, 27)),
    ("내일까지", date(2026, 11, 26)),
    ("12/3까지", date(2026, 12, 3)),
    ("12월 8일", date(2026, 12, 8)),
    ("2026-12-10", date(2026, 12, 10)),
    ("1/5", date(2027, 1, 5)),              # 지난 날짜면 다음 해
    ("다음 회의 전", None),
    ("", None),
    ("미정", None),
])
def test_resolve_due(text, expected):
    assert ac.resolve_due(text, MEETING) == expected


def test_assignee_must_appear_in_evidence():
    raw = [
        {"task": "DB 정의서 수정", "assignee": "지은", "due_text": "금요일까지", "priority": "보통",
         "evidence": "지은이 DB 테이블 정의서를 금요일까지 수정하기로 함."},
        {"task": "발표 자료 제작", "assignee": "민수", "due_text": "", "priority": "높음",
         "evidence": "발표 자료는 누가 할지 아직 못 정함."},  # AI가 담당자를 지어냄
    ]
    actions, warnings = ac.normalize_actions(raw, MEMBERS, SOURCE, MEETING)
    assert actions[0]["assignee"] == "지은" and actions[0]["due"] == "2026-11-27"
    assert actions[1]["assignee"] == "미정"
    assert any("민수" in w for w in warnings)


def test_made_up_evidence_flagged_and_unknown_member():
    raw = [
        {"task": "서버 배포", "assignee": "철수", "due_text": "내일", "evidence": "철수가 서버를 배포하기로 함"},
        {"task": "", "assignee": "지은", "evidence": "x"},  # 할 일 없음 → 제외
    ]
    actions, warnings = ac.normalize_actions(raw, MEMBERS, SOURCE, MEETING)
    assert len(actions) == 1
    assert actions[0]["verified"] is False
    assert actions[0]["assignee"] == "미정"
    assert actions[0]["priority"] == "보통"


def test_decisions_verified():
    decisions = ac.normalize_decisions(
        [{"text": "로그인 제외", "evidence": "희연은 API 명세서를"}, {"text": "가짜", "evidence": "없는 문장"}], SOURCE)
    assert [d["verified"] for d in decisions] == [True, False]
