# MeetMate

대학 팀플용 AI 도우미. 카톡 대화에서 가능 시간을 뽑아 회의 시간을 추천하고(F1), 회의록에서 액션 아이템을 근거와 함께 추출해(F2) GitHub Issues로 등록한다(F3). 상세 요구사항: `docs/PRD.md`

## Commands
- 설치: `pip install -r requirements.txt`
- 실행: `streamlit run app.py`
- 테스트: `pytest -q`

## Tech Stack
- Python 3, Streamlit, requests, python-dotenv, pytest
- LLM: `.env`의 `LLM_PROVIDER`(openrouter | factchat), `LLM_MODEL`로 선택

## 반드시 지킬 규칙
- **API 키·토큰은 반드시 `.env`에서만 읽는다.** 코드·로그·커밋에 키를 절대 넣지 않는다.
- **계산은 코드로, 해석만 AI로.** 시간 교집합, 순위, 날짜 계산은 LLM에 맡기지 말고 `core/schedule.py`, `core/actions.py`의 순수 함수로 구현하고 pytest로 테스트한다.
- **할루시네이션 방지:** LLM 출력은 항상 JSON 스키마로 검증한다. 모든 추출 항목에 `evidence`(원문 문장)를 포함하고, 원문에 실제로 있는지 코드로 확인한다. 원문에 없는 담당자·날짜는 지어내지 말고 `"미정"`으로 둔다.
- LLM 호출 실패 시 앱이 죽지 않게 한다 (1회 재시도 → 사용자에게 오류 안내 → 오프라인 데모 모드 제안).
- 한국어 UI. 변수명·함수명은 영어 snake_case, 주석은 한국어로 짧게.
- 한 번에 한 단계(`docs/prompts/PRD_stepN.md`)만 구현하고, 끝나면 실행 방법과 확인할 점을 요약한다.

## 시간 해석 규칙 (F1 프롬프트에 포함)
- 오전 = 09:00–12:00, 점심 = 12:00–13:00, 오후 = 13:00–18:00, 저녁 = 18:00–22:00
- "N시 이후" = N:00–22:00, "N시 전" = 09:00–N:00, 하루 범위는 09:00–22:00
- 요일 없이 "내일/모레"는 기준 날짜(사용자가 입력)로 계산

## AI 협업 기록
- 단계가 끝날 때마다 `/log` 명령으로 `docs/ai-log/`에 기록한다 (프롬프트, AI 결과 요약, 내 검토/수정 판단, 다음 할 일).
