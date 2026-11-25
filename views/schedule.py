"""F1 약속 잡기: 카톡 대화 → 가능 시간 추출(AI) → 겹치는 시간 계산(코드) → 회의 시간 추천."""
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from core import schedule as sc
from core.llm import LLMError
from core.schedule_ai import extract_slots

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = {"kakao_easy": "샘플 1: 쉬운 대화", "kakao_hard": "샘플 2: 말 바꾸기·애매한 표현"}
DAY_OPTIONS = sc.DAYS
TYPE_LABEL = {"available": "가능", "unavailable": "불가능"}
TYPE_FROM_LABEL = {v: k for k, v in TYPE_LABEL.items()}
COLUMNS = ["팀원", "요일", "시작", "끝", "구분", "근거", "근거 확인"]

st.title("🗓️ 약속 잡기")
st.caption("단톡방 대화를 붙여넣으면 AI가 팀원별로 되는 시간을 뽑고, 겹치는 시간은 코드가 계산해요.")

# ---------- 기본 설정 ----------
c1, c2, c3 = st.columns([3, 1, 1])
members_text = c1.text_input("팀원 이름 (쉼표로 구분)", value=st.session_state.get("team", "민수, 지은, 희연, 도윤"))
st.session_state["team"] = members_text
duration = c2.selectbox("회의 길이", [30, 60, 90, 120], index=1, format_func=lambda m: f"{m}분")
base_date = c3.date_input("기준 날짜", value=st.session_state.get("base_date", date.today()))
deadline = st.session_state.get("deadline")
if deadline:
    st.info(f"대시보드에서 왔어요. 가장 가까운 마감({deadline:%m/%d}) 전에 회의를 잡는 걸 추천해요.")
default_available = st.checkbox("아무 말도 안 한 팀원은 언제든 가능한 것으로 보기", value=True)
members = [m.strip() for m in members_text.split(",") if m.strip()]


def slots_to_df(slots: list[dict]) -> pd.DataFrame:
    rows = [{
        "팀원": s["member"], "요일": s["day"], "시작": s["start"], "끝": s["end"],
        "구분": TYPE_LABEL[s["type"]], "근거": s.get("evidence", ""),
        "근거 확인": "✅" if s.get("verified") else ("⚠️ 없음" if s.get("evidence") else "직접 입력"),
    } for s in slots]
    return pd.DataFrame(rows, columns=COLUMNS)


def df_to_slots(df: pd.DataFrame) -> tuple[list[dict], list[str]]:
    raw = []
    for _, r in df.dropna(how="all").fillna("").iterrows():
        raw.append({
            "member": r.get("팀원"), "day": r.get("요일"), "start": r.get("시작"), "end": r.get("끝"),
            "type": TYPE_FROM_LABEL.get(r.get("구분"), "available"), "evidence": r.get("근거") or "",
        })
    return sc.validate_slots(raw, members)


def slot_editor(df: pd.DataFrame, key: str) -> pd.DataFrame:
    return st.data_editor(
        df, key=key, num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "팀원": st.column_config.SelectboxColumn(options=members, required=True),
            "요일": st.column_config.SelectboxColumn(options=DAY_OPTIONS, required=True,
                                                    help="MON=월 TUE=화 WED=수 THU=목 FRI=금 SAT=토 SUN=일"),
            "시작": st.column_config.TextColumn(help="HH:MM (예: 18:00)", required=True),
            "끝": st.column_config.TextColumn(help="HH:MM (예: 22:00)", required=True),
            "구분": st.column_config.SelectboxColumn(options=["가능", "불가능"], required=True),
            "근거": st.column_config.TextColumn(width="large"),
            "근거 확인": st.column_config.TextColumn(disabled=True),
        },
    )


def show_results(slots: list[dict]):
    grid = sc.build_grid(slots, members, default_available=default_available)
    recs = sc.recommend(grid, members, duration)

    st.subheader("추천 회의 시간")
    if not recs:
        st.warning("모두 또는 1명 빼고 가능한 시간이 없어요. 회의 길이를 줄이거나 시간을 다시 조율해 보세요.")
    else:
        cols = st.columns(len(recs))
        for i, (col, r) in enumerate(zip(cols, recs), 1):
            meet_date = sc.next_date(r["day"], base_date)
            with col.container(border=True):
                st.markdown(f"**{i}순위** · {'전원 가능 ✅' if r['full'] else '1명 불참 ⚠️'}")
                st.markdown(f"### {sc.DAY_KO[r['day']]}요일 {r['meeting_start']}–{r['meeting_end']}")
                st.write(f"📅 {meet_date:%m/%d} · 가능 구간 {r['start']}–{r['end']}")
                if deadline and meet_date > deadline:
                    st.write(f":orange[⚠️ 마감({deadline:%m/%d}) 이후예요]")
                st.write(f"참석 {len(r['members'])}/{len(members)}명: {', '.join(r['members'])}")
                if r["missing"]:
                    st.write(f"불참: **{', '.join(r['missing'])}**")
                ics = sc.to_ics("팀 회의 (MeetMate)", meet_date, r["meeting_start"], r["meeting_end"],
                                f"참석: {', '.join(r['members'])}")
                st.download_button("캘린더에 추가 (.ics)", ics.encode("utf-8"), file_name=f"meeting_{meet_date:%Y%m%d}.ics",
                                   mime="text/calendar", key=f"ics_{i}_{r['day']}_{r['start']}")

    st.subheader("요일·시간별 가능 인원")
    counts = sc.count_table(grid)
    heat = pd.DataFrame({f"{sc.DAY_KO[d]}": counts[d] for d in sc.DAYS}, index=sc.cell_times())
    n = max(len(members), 1)

    def color(v):
        if v == n:
            return "background-color: #D9622B; color: white; font-weight: 700"
        return f"background-color: rgba(47,95,208,{0.08 + 0.6 * v / n:.2f})"

    st.dataframe(heat.style.map(color), width="stretch", height=560)
    st.caption(f"주황색 = {n}명 전원 가능 · 파란색이 진할수록 가능한 사람이 많아요.")


if len(members) < 2:
    st.info("팀원을 2명 이상 입력하세요.")
    st.stop()

tab_chat, tab_manual = st.tabs(["💬 카톡 대화로 찾기", "✍️ 직접 입력"])

# ---------- 탭 1: 카톡 ----------
with tab_chat:
    b1, b2, _ = st.columns([1, 1, 2])
    for btn, (key, label) in zip((b1, b2), SAMPLES.items()):
        if btn.button(label, width="stretch"):
            st.session_state["chat_text"] = (ROOT / "samples" / f"{key}.txt").read_text(encoding="utf-8")
            st.session_state["sample_key"] = key
            st.session_state.pop("schedule_extracted", None)

    chat_text = st.text_area("단톡방 대화 붙여넣기", key="chat_text", height=220,
                             placeholder="[민수] 나는 화요일 3시 이후 괜찮아\n[지은] 화요일은 5시 이후 가능 ...")

    if st.button("🔍 가능 시간 추출", type="primary", disabled=not chat_text.strip()):
        sample_key = st.session_state.get("sample_key")
        demo_key = sample_key if sample_key and chat_text == (ROOT / "samples" / f"{sample_key}.txt").read_text(encoding="utf-8") else None
        with st.spinner("AI가 대화를 읽는 중..."):
            try:
                st.session_state["schedule_extracted"] = extract_slots(chat_text, members, base_date, demo_key=demo_key)
            except LLMError as e:
                st.error(str(e))

    ext = st.session_state.get("schedule_extracted")
    if ext:
        st.markdown("**AI가 뽑은 시간** — 틀린 곳은 표에서 직접 고치거나 행을 추가·삭제하세요.")
        edited = slot_editor(slots_to_df(ext["slots"]), key="chat_editor")
        for w in ext["warnings"]:
            st.warning(w)
        if ext["notes"]:
            with st.expander("AI 판단 메모", expanded=True):
                for note in ext["notes"]:
                    st.write(f"- {note}")
        slots, edit_warnings = df_to_slots(edited)
        for w in edit_warnings:
            st.warning(f"표 입력 확인: {w}")
        show_results(slots)

# ---------- 탭 2: 직접 입력 ----------
with tab_manual:
    st.write("카톡 없이 팀원별로 되는/안 되는 시간을 직접 입력해요. 아래 표에 행을 추가하세요.")
    if "manual_df" not in st.session_state:
        st.session_state["manual_df"] = pd.DataFrame(columns=COLUMNS)
    manual = slot_editor(st.session_state["manual_df"], key="manual_editor")
    slots, edit_warnings = df_to_slots(manual)
    for w in edit_warnings:
        st.warning(f"표 입력 확인: {w}")
    if slots:
        show_results(slots)
