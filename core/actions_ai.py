"""회의록 → 결정 사항·할 일 추출 (AI는 해석만, 날짜 계산·검증은 actions.py)."""
from __future__ import annotations

from datetime import date

from core.actions import normalize_actions, normalize_decisions
from core.llm import ask_json

SYSTEM_PROMPT = """너는 대학생 팀프로젝트 회의록에서 '결정 사항'과 '할 일'을 뽑아내는 도우미다.

[팀원 목록] {members}
[회의 날짜] {meeting_date}

[출력 형식] JSON 객체 하나:
{{"decisions": [{{"text": "결정된 내용 한 문장", "evidence": "회의록 원문 문장 그대로"}}],
 "actions": [{{"task": "할 일 (동사로 끝나게 짧게)", "assignee": "팀원 이름 또는 미정", "due_text": "회의록에 적힌 기한 표현 그대로 또는 빈 문자열", "priority": "높음|보통|낮음", "evidence": "회의록 원문 문장 그대로"}}]}}

[규칙]
1. assignee 는 회의록에 '누가 하기로 했는지' 이름이 명시된 경우에만 쓴다. 이름이 없거나 아직 못 정했으면 반드시 "미정".
2. due_text 는 날짜를 계산하지 말고 회의록 표현을 그대로 옮긴다 (예: "금요일까지", "다음 주 월요일까지", "다음 회의 전"). 기한이 없으면 "".
3. 담당자를 정하지 못한 일, 다음 회의에서 정하기로 한 일도 할 일로 넣는다 (assignee "미정").
4. evidence 는 회의록에서 그대로 복사한다. 요약하거나 고치지 않는다.
5. 회의록에 없는 할 일, 담당자, 기한은 절대 지어내지 않는다.
6. priority: 마감이 가깝거나 발표·제출과 직결되면 높음, 나머지는 보통.
"""


def extract_actions(minutes_text: str, members: list[str], meeting_date: date, demo_key: str | None = None) -> dict:
    """반환: {"decisions": [...], "actions": [...], "warnings": [...]}. 실패 시 LLMError."""
    system = SYSTEM_PROMPT.format(members=", ".join(members), meeting_date=meeting_date.isoformat())
    data = ask_json(system, minutes_text, demo_key=demo_key)
    actions, warnings = normalize_actions(data.get("actions", []), members, minutes_text, meeting_date)
    decisions = normalize_decisions(data.get("decisions", []), minutes_text)
    for d in decisions:
        if not d["verified"]:
            warnings.append(f"결정 사항 '{d['text']}': 근거 문장이 회의록에 없어요.")
    return {"decisions": decisions, "actions": actions, "warnings": warnings}
