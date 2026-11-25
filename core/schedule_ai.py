"""카톡 대화 → 팀원별 가능/불가능 시간 추출 (AI는 해석만, 계산은 schedule.py)."""
from __future__ import annotations

from datetime import date

from core.evidence import evidence_in_source
from core.llm import ask_json
from core.schedule import DAY_KO, DAYS, validate_slots

SYSTEM_PROMPT = """너는 대학생 팀플 단톡방 대화에서 팀원별 '가능한 시간'과 '불가능한 시간'만 뽑아내는 도우미다.
계산이나 추천은 하지 말고, 대화에 적힌 시간 정보만 구조화하라.

[팀원 목록] {members}
[기준 날짜] {base_date} ({base_day}요일) — "오늘/내일/모레"는 이 날짜 기준으로 요일을 정한다.

[출력 형식] JSON 객체 하나:
{{"slots": [{{"member": "팀원 이름", "day": "MON|TUE|WED|THU|FRI|SAT|SUN", "start": "HH:MM", "end": "HH:MM", "type": "available|unavailable", "evidence": "그 팀원이 쓴 원문 문장 그대로"}}],
 "notes": ["애매해서 판단이 필요했던 부분을 한국어로 짧게"]}}

[규칙]
1. member 는 팀원 목록의 이름과 글자까지 똑같이 쓴다. 목록에 없는 사람은 넣지 않는다.
2. 시간은 24시간 HH:MM. 하루 범위는 09:00~22:00 이다.
3. 시간 표현 해석: 오전=09:00~12:00, 점심=12:00~13:00, 오후=13:00~18:00, 저녁=18:00~22:00,
   "N시 이후"=N시~22:00, "N시 전/까지만"=09:00~N시, "하루 종일/아무 때나"=09:00~22:00.
   오후 시간대 숫자(예: "3시", "7시")는 대학생 일정 맥락상 오후(15:00, 19:00)로 본다.
4. "안 돼, 불가, 수업, 알바, 약속 있어"는 unavailable. 시간 언급 없이 요일만 안 되면 09:00~22:00 unavailable.
5. 한 사람이 말을 바꾸면 마지막 말을 따른다. 취소한 가능 시간은 unavailable 로 바꿔 적고 notes 에 남긴다.
6. 다른 사람 제안에 동의만 한 경우("ㅇㅋ", "좋아", 이모티콘)는 슬롯을 만들지 말고 notes 에 적는다.
7. evidence 는 반드시 그 팀원의 메시지에서 그대로 복사한다. 요약하거나 바꾸지 않는다.
8. 대화에 없는 시간은 절대 지어내지 않는다. 시간 언급이 없는 팀원은 슬롯을 만들지 않는다.
"""


def build_system_prompt(members: list[str], base_date: date) -> str:
    return SYSTEM_PROMPT.format(
        members=", ".join(members),
        base_date=base_date.isoformat(),
        base_day=DAY_KO[DAYS[base_date.weekday()]],
    )


def extract_slots(chat_text: str, members: list[str], base_date: date, demo_key: str | None = None) -> dict:
    """반환: {"slots": [...근거 확인 포함], "warnings": [...], "notes": [...]}. 실패 시 LLMError."""
    data = ask_json(build_system_prompt(members, base_date), chat_text, demo_key=demo_key)
    slots, warnings = validate_slots(data.get("slots", []), members)
    for s in slots:
        s["verified"] = evidence_in_source(s["evidence"], chat_text)
        if not s["verified"]:
            warnings.append(f"{s['member']} {DAY_KO[s['day']]} {s['start']}~{s['end']}: 근거 문장이 대화에 없음 (확인 필요)")
    notes = [str(n) for n in data.get("notes", []) if str(n).strip()]
    return {"slots": slots, "warnings": warnings, "notes": notes}
