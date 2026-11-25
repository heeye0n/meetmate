# Step 1 — 프로젝트 골격 + LLM 연결

## 목표
Streamlit 앱 뼈대와 LLM 호출 모듈을 만들고, 실제 API 호출이 되는지 확인한다. 기능은 아직 만들지 않는다.

## 할 일
1. `requirements.txt` (streamlit, requests, python-dotenv, pytest)
2. `app.py`: 홈 화면 (앱 소개 + 3개 페이지 안내), 사이드바 메뉴
3. `views/home.py`, `views/schedule.py`, `views/minutes.py`, `views/dashboard.py` (`st.navigation`으로 메뉴 이름만 한글, 파일명은 영어): 제목만 있는 빈 페이지
4. `core/llm.py`
   - `.env`에서 `LLM_PROVIDER`, `LLM_MODEL`, `OPENROUTER_API_KEY`, `FACTCHAT_API_KEY` 읽기
   - `ask_json(system_prompt, user_text, schema_hint) -> dict` 함수: JSON만 받도록 요청, 파싱 실패 시 1회 재시도, 그래도 실패하면 예외를 친절한 메시지로 변환
   - openrouter: `https://openrouter.ai/api/v1/chat/completions` (OpenAI 호환)
   - factchat: `https://factchat-cloud.mindlogic.ai/v1/gateway/claude/v1/messages` (Anthropic 형식, `user-agent` 헤더 필요, `max_tokens` 1024 이상)
   - 같은 입력은 `data/cache/`에 캐시
   - `DEMO_MODE=true`면 API 대신 `samples/demo_responses/`의 JSON을 반환
5. 홈 화면에 "LLM 연결 테스트" 버튼 → 간단한 JSON 응답을 받아 표시

## 확인 방법
- `streamlit run app.py` 실행 → 사이드바에 3개 페이지 보임
- 연결 테스트 버튼 → JSON 응답 표시 (키가 틀리면 앱이 죽지 않고 안내 메시지)
- `.env`가 `git status`에 나오지 않음

## Claude Code에 넣을 프롬프트
```
@docs/PRD.md 와 CLAUDE.md 를 읽고 docs/prompts/PRD_step1.md 를 실행해.
끝나면 실행 방법과 내가 직접 확인해야 할 점을 알려줘.
```
