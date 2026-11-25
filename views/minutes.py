"""F2 회의록 정리 + F3 GitHub 이슈 등록 + F5 회의 저장."""
import re
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from core import github_issues as gh
from core import storage
from core.actions_ai import extract_actions
from core.llm import LLMError

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = {"meeting_01": "샘플 1: 첫 회의", "meeting_02": "샘플 2: 다음 회의(점검)"}
UNASSIGNED = "미정"

st.title("📝 회의록 정리")
st.caption("회의록을 넣으면 할 일 · 담당자 · 마감일을 회의록 원문 근거와 함께 뽑아요. 회의록에 없는 담당자·날짜는 지어내지 않고 '미정'으로 둬요.")


# ---------- 입력 콜백 (위젯을 그리기 전에 값 넣기) ----------
def sample_text(key: str) -> str:
    return (ROOT / "samples" / f"{key}.txt").read_text(encoding="utf-8")


def load_sample(key: str):
    text = sample_text(key)
    st.session_state["minutes_text"] = text
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        st.session_state["meeting_date"] = date(*map(int, m.groups()))
    title = re.search(r"안건:\s*(.+)", text)
    if title:
        st.session_state["meeting_title"] = title.group(1).strip()
    for k in ("extracted", "meeting_id", "issue_results"):
        st.session_state.pop(k, None)


def load_upload():
    f = st.session_state.get("upload")
    if f is None:
        return
    raw = f.getvalue()
    for enc in ("utf-8", "cp949"):
        try:
            st.session_state["minutes_text"] = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    for k in ("extracted", "meeting_id", "issue_results"):
        st.session_state.pop(k, None)


b1, b2, b3 = st.columns([1, 1, 2])
for btn, (key, label) in zip((b1, b2), SAMPLES.items()):
    btn.button(label, on_click=load_sample, args=(key,), width="stretch")
b3.file_uploader("회의록 파일 (.txt, .md)", type=["txt", "md"], key="upload", on_change=load_upload,
                 label_visibility="collapsed")

st.session_state.setdefault("meeting_date", date.today())
c1, c2, c3 = st.columns([1, 2, 2])
meeting_date = c1.date_input("회의 날짜", key="meeting_date")
meeting_title = c2.text_input("회의 제목", key="meeting_title", placeholder="예: 중간 발표 피드백 회의")
members_text = c3.text_input("팀원 이름 (쉼표로 구분)", value=st.session_state.get("team", "민수, 지은, 희연, 도윤"))
st.session_state["team"] = members_text
members = [m.strip() for m in members_text.split(",") if m.strip()]

minutes_text = st.text_area("회의록", key="minutes_text", height=260,
                            placeholder="회의 날짜, 참석자, 논의 내용, 누가 무엇을 언제까지 하기로 했는지...")

if st.button("🔍 할 일 추출", type="primary", disabled=not minutes_text.strip() or not members):
    demo_key = next((k for k in SAMPLES if minutes_text == sample_text(k)), None)
    with st.spinner("AI가 회의록을 읽는 중..."):
        try:
            st.session_state["extracted"] = extract_actions(minutes_text, members, meeting_date, demo_key=demo_key)
            st.session_state.pop("meeting_id", None)
            st.session_state.pop("issue_results", None)
        except LLMError as e:
            st.error(str(e))

ext = st.session_state.get("extracted")
if not ext:
    st.stop()

# ---------- 결정 사항 ----------
st.subheader("결정 사항")
if ext["decisions"]:
    for d in ext["decisions"]:
        mark = "✅" if d["verified"] else "⚠️ 근거 없음"
        st.markdown(f"- **{d['text']}** {mark}  \n  <small>“{d['evidence']}”</small>", unsafe_allow_html=True)
else:
    st.write("뽑힌 결정 사항이 없어요.")

# ---------- 할 일 표 ----------
st.subheader("할 일")
st.caption("틀린 곳은 표에서 직접 고치세요. 마감은 YYYY-MM-DD 형식, 비우면 미정이에요. '등록'에 체크한 항목만 GitHub 이슈로 올라가요.")

df = pd.DataFrame([{
    "등록": a["assignee"] != UNASSIGNED,
    "할 일": a["task"],
    "담당": a["assignee"],
    "마감": a["due"] or "",
    "기한 표현": a["due_text"],
    "우선순위": a["priority"],
    "근거": a["evidence"],
    "근거 확인": "✅" if a["verified"] else "⚠️ 없음",
} for a in ext["actions"]])

edited = st.data_editor(
    df, key="actions_editor", num_rows="dynamic", hide_index=True, width="stretch",
    column_config={
        "등록": st.column_config.CheckboxColumn(width="small"),
        "할 일": st.column_config.TextColumn(width="medium", required=True),
        "담당": st.column_config.SelectboxColumn(options=members + [UNASSIGNED], required=True),
        "마감": st.column_config.TextColumn(help="YYYY-MM-DD, 비우면 미정"),
        "기한 표현": st.column_config.TextColumn(disabled=True, help="회의록에 적힌 원래 표현"),
        "우선순위": st.column_config.SelectboxColumn(options=["높음", "보통", "낮음"]),
        "근거": st.column_config.TextColumn(width="large"),
        "근거 확인": st.column_config.TextColumn(disabled=True),
    },
)
for w in ext["warnings"]:
    st.warning(w)


def rows_to_actions(frame: pd.DataFrame) -> tuple[list[dict], list[bool], list[str]]:
    actions, selected, problems = [], [], []
    for _, r in frame.dropna(how="all").fillna("").iterrows():
        task = str(r["할 일"]).strip()
        if not task:
            continue
        due = str(r["마감"]).strip() or None
        if due:
            try:
                date.fromisoformat(due)
            except ValueError:
                problems.append(f"'{task}' 마감 '{due}'는 날짜 형식(YYYY-MM-DD)이 아니라 미정으로 처리해요.")
                due = None
        actions.append({
            "task": task, "assignee": str(r["담당"]) or UNASSIGNED, "due": due, "due_text": str(r["기한 표현"]),
            "priority": str(r["우선순위"]) or "보통", "evidence": str(r["근거"]),
            "verified": str(r["근거 확인"]).startswith("✅"),
        })
        selected.append(bool(r["등록"]))
    return actions, selected, problems


actions, selected, problems = rows_to_actions(edited)
for p in problems:
    st.warning(p)

meeting = {
    "date": meeting_date.isoformat(), "title": meeting_title.strip(), "attendees": members,
    "decisions": ext["decisions"], "actions": actions, "minutes": minutes_text,
}

# ---------- 저장 / 이슈 등록 ----------
st.subheader("다음 단계")
s1, s2 = st.columns(2)

with s1.container(border=True):
    st.markdown("**💾 회의 저장**")
    st.write("대시보드에서 진행 상황을 보려면 저장하세요.")
    if st.button("이 회의 저장", width="stretch"):
        if st.session_state.get("meeting_id"):
            meeting["id"] = st.session_state["meeting_id"]  # 다시 누르면 덮어쓰기
        st.session_state["meeting_id"] = storage.save_meeting(meeting)
        st.success(f"저장했어요. 할 일 {len(actions)}개 · 대시보드에서 확인하세요.")

cfg = gh.get_github_config()
with s2.container(border=True):
    st.markdown("**🐙 GitHub 이슈 등록**")
    n_sel = sum(selected)
    if not cfg["ready"]:
        st.write("`.env` 에 GITHUB_TOKEN 과 GITHUB_REPO 를 넣으면 버튼 한 번으로 이슈를 만들 수 있어요. 지금은 아래 체크리스트를 복사해 쓰세요.")
    else:
        st.write(f"저장소 `{cfg['repo']}` 에 체크한 {n_sel}개를 이슈로 등록해요.")
    if st.button(f"선택한 {n_sel}개 이슈 등록", disabled=not cfg["ready"] or n_sel == 0, width="stretch"):
        mapping = storage.load_members()
        results = []
        with st.spinner("GitHub에 등록하는 중..."):
            for a, sel in zip(actions, selected):
                if not sel:
                    continue
                title, body = gh.build_issue(a, meeting)
                ok, res, note = gh.create_issue(cfg["repo"], cfg["token"], title, body,
                                                labels=["meetmate"], assignee=mapping.get(a["assignee"]))
                results.append((a["task"], ok, res, note))
                if ok:
                    a["issue_url"] = res
        st.session_state["issue_results"] = results
        if st.session_state.get("meeting_id"):  # 저장된 회의면 이슈 링크도 반영
            meeting["id"] = st.session_state["meeting_id"]
            storage.save_meeting(meeting)

for task, ok, res, note in st.session_state.get("issue_results", []):
    if ok:
        st.success(f"{task} → [{res}]({res})" + (f"  \n{note}" if note else ""))
    else:
        st.error(f"{task}: {res}")

with st.expander("📋 Markdown 체크리스트 (카톡·노션·README에 붙여넣기)", expanded=not cfg["ready"]):
    st.code(gh.markdown_checklist(actions) or "(할 일 없음)", language="markdown")

with st.expander("👥 팀원 GitHub 아이디 연결 (이슈 담당자 지정용)"):
    mapping = storage.load_members()
    mdf = pd.DataFrame([{"팀원": m, "GitHub 아이디": mapping.get(m, "")} for m in members])
    medit = st.data_editor(mdf, key="members_editor", hide_index=True, width="stretch",
                           column_config={"팀원": st.column_config.TextColumn(disabled=True)})
    if st.button("아이디 저장"):
        storage.save_members(dict(zip(medit["팀원"], medit["GitHub 아이디"].fillna(""))))
        st.success("저장했어요. (data/members.json, GitHub에는 올라가지 않아요)")
