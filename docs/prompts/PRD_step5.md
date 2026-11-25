# Step 5 — 서브에이전트 리뷰 + Playwright 자동 테스트 + GitHub 업로드

> 이 단계는 **직접 실행**한다. 실행 화면을 캡처해 `docs/screenshots/`에 넣고, 끝날 때마다 `/log`.
> 준비된 것: `.claude/agents/`에 서브에이전트 3개(code-reviewer, fixer, ux-advisor), git 첫 커밋

## 0. 시작하기
1. 파일 탐색기에서 `C:\Users\user\VibeCoding\MeetMate` 열기 → 빈 곳 우클릭 → [터미널에서 열기]
2. `claude` 입력

## 1. 서브에이전트 확인 (13·14강)
```
/agents
```
→ Project agents에 `code-reviewer`(파랑, 읽기 전용), `fixer`(초록), `ux-advisor`(주황)가 보이는지 확인 → 화면 캡처 → [Esc]

> 수업처럼 직접 만들어 보고 싶으면 `Create new agent` → `Project` → `Generate with Claude`로 하나 더 만들어도 좋다 (예: 시연 시나리오 점검 에이전트).

## 2. 서브에이전트 협업 리뷰
```
code-reviewer로 전체 코드를 리뷰한 뒤, 발견한 문제를 fixer가 수정하고 pytest를 통과시킨 다음, ux-advisor가 사용자 경험을 개선하게 해줘. 각 에이전트 결과를 요약해서 보여줘.
```
- 권한 요청은 내용을 읽고 `1. Yes` (반복되면 `2. Yes, and don't ask again`)
- 끝나면: `/log 서브에이전트 리뷰` → 리뷰에서 나온 문제 중 **내가 동의/반대한 것**을 로그에 직접 적기 (발표 소재)

## 3. Playwright MCP 설치 (16강)
claude 안에서 `/exit`로 나온 뒤 터미널에:
```
claude mcp add playwright -- cmd /c npx -y @playwright/mcp@latest
claude mcp list
```
→ `playwright`가 보이면 성공

## 4. 앱 켜기 (데모 모드)
`.env`가 `DEMO_MODE=true`인지 확인. 새 터미널 창을 하나 더 열고:
```
streamlit run app.py
```
(이미 켜져 있으면 생략. 주소: http://localhost:8501)

## 5. Playwright 자동 테스트
원래 터미널에서 `claude` 다시 실행 후:
```
Playwright MCP로 http://localhost:8501 의 MeetMate를 테스트해줘. Streamlit 앱이라 화면이 바뀔 때마다 1~2초 기다려.
시나리오1 (약속 잡기): 왼쪽 메뉴 [약속 잡기] → [샘플 1: 쉬운 대화] → [🔍 가능 시간 추출] → 추천 카드 1순위가 "화요일 18:00–19:00"이고 "전원 가능"인지 확인 → [샘플 2: 말 바꾸기·애매한 표현]으로도 반복해서 1순위가 "목요일 18:30–19:30"인지 확인
시나리오2 (회의록 정리): [회의록 정리] → [샘플 1: 첫 회의] → [🔍 할 일 추출] → 할 일 6개, 지은 마감 2026-11-27, 발표 자료 담당 "미정"인지 확인 → [이 회의 저장] → [샘플 2: 다음 회의(점검)]도 추출 후 저장
시나리오3 (대시보드): [대시보드] → 기준 날짜를 2026-12-03으로 바꾸고 전체 할 일 11개, 마감 지남 2개, 마감 임박 4개인지 확인 → [다음 회의 잡기 →]를 눌러 약속 잡기 화면으로 이동하는지 확인
각 시나리오 끝에 스크린샷을 docs/screenshots/ 에 저장하고, 통과/실패와 실패 원인을 표로 보고해줘.
```
- 실패하면 원인을 보고 수정 요청 → 다시 테스트 (이 과정이 기록 점수의 핵심)
- 끝나면: `/log Playwright 테스트`
- 테스트 후 대시보드 데이터를 지우려면 `data/meetings.json` 삭제

## 6. GitHub 업로드
1. github.com → New repository → 이름 `MeetMate`, **README 추가하지 않기** → Create
2. Claude Code(이 대화)에 "저장소 만들었어"라고 알려주면 push
   - 또는 직접: `git remote add origin https://github.com/heeye0n/MeetMate.git` → `git push -u origin main`
3. GitHub 페이지에서 `.env`가 없는지 확인

## 확인 체크리스트
- [ ] `/agents` 화면 캡처
- [ ] 서브에이전트 리뷰 결과 + 수정 내역 로그
- [ ] Playwright 스크린샷 3장 이상 (`docs/screenshots/`)
- [ ] pytest 전부 통과
- [ ] GitHub 저장소에 `.env` 없음
