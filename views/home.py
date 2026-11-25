import streamlit as st

from core.llm import LLMError, ask_json, get_config

st.title("🗓️ MeetMate")
st.markdown("#### 카톡으로 약속 잡고, 회의록은 할 일로.")
st.write("대학 팀플의 **약속 잡기 → 회의 → 할 일 정리 → 실행**을 한 곳에서 끝내는 AI 회의 도우미예요.")

c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("① 약속 잡기")
    st.write("단톡방 대화를 붙여넣으면 모두 가능한 회의 시간을 추천해요.")
with c2:
    st.subheader("② 회의록 정리")
    st.write("회의록에서 할 일 · 담당자 · 마감일을 원문 근거와 함께 뽑아요.")
with c3:
    st.subheader("③ 대시보드")
    st.write("팀원별 진행률과 마감 임박 할 일을 한눈에 봐요.")

st.markdown("##### 시연 순서")
l1, l2, l3 = st.columns(3)
l1.page_link("views/schedule.py", label="① 약속 잡기 — 샘플 대화로 회의 시간 찾기", icon="🗓️")
l2.page_link("views/minutes.py", label="② 회의록 정리 — 샘플 1·2 추출 후 저장", icon="📝")
l3.page_link("views/dashboard.py", label="③ 대시보드 — 진행 현황, 다음 회의 잡기", icon="📊")

st.divider()
st.subheader("AI 연결 상태")

cfg = get_config()
if cfg["demo_mode"]:
    st.info("데모 모드가 켜져 있어요. AI를 호출하지 않고 저장된 응답을 사용해요. (.env 의 DEMO_MODE)")
else:
    st.write(f"- 제공자: `{cfg['provider']}`")
    st.write(f"- 모델: `{cfg['model'] or '(비어 있음)'}`")
    st.write(f"- API 키({cfg['key_name']}): {'입력됨 ✅' if cfg['has_key'] else '없음 ⚠️'}")

if st.button("AI 연결 테스트", type="primary"):
    with st.spinner("AI에게 물어보는 중..."):
        try:
            result = ask_json(
                '너는 연결 테스트용 도우미다. {"ok": true, "message": "<한국어로 짧은 인사 한 문장>"} 형식으로만 답하라.',
                "연결 테스트입니다.",
                demo_key="connection_test",
                use_cache=False,
            )
        except LLMError as e:
            st.error(str(e))
        else:
            st.success("연결 성공!")
            st.json(result)
