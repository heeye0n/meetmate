# Step 2 — F1 약속 잡기 (카톡 → 가능 시간 → 회의 시간 추천)

## 목표
카톡 대화를 붙여넣으면 팀원별 가능 시간을 추출하고, 코드로 교집합을 계산해 회의 시간 Top 3을 추천한다.

## 할 일
1. `core/schedule.py` (순수 Python, LLM 사용 금지)
   - 데이터 형식: `{"member", "day"(MON~SUN), "start"("HH:MM"), "end", "type"(available|unavailable), "evidence"}`
   - `build_grid(slots, members, unit_minutes=30)`: 요일×30분 칸별 가능 인원 계산. 아무 말도 없는 팀원의 기본값은 "가능"(옵션으로 "불가능" 전환)
   - `recommend(grid, duration_minutes, top_n=3)`: 전원 가능 → 없으면 (N-1)명 가능 순으로 연속 구간 찾기, 빠지는 사람 표시
   - `to_ics(meeting)`: `.ics` 문자열 생성
2. `tests/test_schedule.py`: 겹침 있음 / 겹침 없음 / 불가능 시간이 가능 시간을 덮는 경우 / 경계(22:00) 테스트
3. `views/schedule.py`
   - 입력: 팀원 이름(쉼표), 회의 길이(30/60/90/120분), 기준 날짜, 카톡 대화 텍스트 영역 (+ `samples/kakao_*.txt` 불러오기 버튼)
   - [시간 추출] → `core/llm.py`로 JSON 추출 (CLAUDE.md의 시간 해석 규칙을 시스템 프롬프트에 포함)
   - 추출 결과를 `st.data_editor` 표로 보여 주고 사용자가 수정 가능, evidence가 원문에 없으면 ⚠️
   - [회의 시간 추천] → 히트맵(요일×시간, 가능 인원 색) + Top 3 카드 + `.ics` 다운로드 버튼
   - 그리드 직접 입력 탭: 팀원 선택 후 칸 체크 (카톡 없이도 사용 가능)

## 확인 방법
- `pytest -q` 통과
- `samples/kakao_easy.txt` → 정답 `samples/expected_kakao_easy.json`과 추출 결과 비교
- `samples/kakao_hard.txt`(번복, 애매한 표현) → 어디서 틀리는지 기록하고 프롬프트 개선 (이 과정을 /log에 꼭 남기기)

## Claude Code에 넣을 프롬프트
```
docs/prompts/PRD_step2.md 를 실행해. schedule.py는 먼저 테스트를 작성하고 통과시킨 뒤에 페이지를 만들어줘.
```
