# Step 3 — F2 회의록 → 액션 아이템 + F3 GitHub Issues 등록

## 목표
회의록에서 할 일·담당자·마감일을 근거 문장과 함께 추출하고, 검토 후 GitHub Issues로 등록한다.

## 할 일
1. `core/actions.py`
   - LLM 추출 형식: `{"decisions":[{"text","evidence"}], "actions":[{"task","assignee","due_text","priority","evidence"}]}`
   - `verify_evidence(items, source_text)`: evidence가 원문에 있는지 검사 (공백·문장부호 무시 부분 일치) → `verified: bool`
   - `resolve_due(due_text, meeting_date)`: "다음 주 금요일", "모레", "12/3까지" → 날짜. 해석 불가면 `None`(=미정)
   - 원문에 없는 담당자는 `"미정"`으로 강제
2. `tests/test_actions.py`: 상대 날짜 계산, 근거 검증 테스트
3. `core/github_issues.py`
   - `.env`의 `GITHUB_TOKEN`, `GITHUB_REPO`(예: heeye0n/MeetMate-demo) 사용
   - `create_issue(title, body, labels, assignee)` → 이슈 URL 반환, 실패 시 이유 반환
   - 팀원 이름 → GitHub 아이디 매핑은 `data/members.json`
4. `views/minutes.py`
   - 입력: 회의 날짜, 참석자, 회의록 텍스트/파일 업로드 (+ `samples/meeting_*.txt` 불러오기)
   - [액션 아이템 추출] → 결정 사항 목록 + 액션 아이템 `st.data_editor` (✅ 근거 확인 / ⚠️ 근거 없음 표시)
   - 선택한 항목 [GitHub 이슈 등록] → 생성된 이슈 링크 표시
   - 토큰이 없으면 [Markdown 체크리스트 복사]로 대체
   - [이 회의 저장] → `core/storage.py`로 `data/meetings.json`에 저장

## 확인 방법
- `samples/meeting_01.txt`에서 할 일이 빠짐없이, 지어냄 없이 나오는지 직접 채점
- 테스트용 저장소에 이슈가 실제로 생성되는지 확인

## Claude Code에 넣을 프롬프트
```
docs/prompts/PRD_step3.md 를 실행해. GitHub 토큰은 .env에서만 읽고, 토큰이 없을 때도 앱이 정상 동작하게 해줘.
```
