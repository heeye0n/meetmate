"""F4 대시보드 + F5 회의 이력: 팀 진행 현황, 마감 임박, 다음 회의 안건."""
from datetime import date

import pandas as pd
import streamlit as st

from core import dashboard as db
from core import storage

STATUS_ICON = {"할 일": "⬜", "진행 중": "🟦", "완료": "✅"}

head, right = st.columns([3, 1])
head.title("📊 대시보드")
today = right.date_input("기준 날짜 (오늘)", value=date.today(), help="시연할 때 날짜를 바꿔 볼 수 있어요.")

meetings = storage.load_meetings()
if not meetings:
    st.info("아직 저장된 회의가 없어요. 회의록 정리에서 회의를 저장하면 여기에 나타나요.")
    st.page_link("views/minutes.py", label="회의록 정리로 가기", icon="📝")
    st.stop()

items = db.flatten(meetings)
s = db.summary(items, today)

# ---------- 상단 지표 ----------
m1, m2, m3, m4 = st.columns(4)
m1.metric("전체 할 일", f"{s['total']}개", f"진행 중 {s['in_progress']}개", delta_color="off")
m2.metric("완료율", f"{s['done_rate']}%", f"완료 {s['done']}개", delta_color="off")
m3.metric("마감 임박 (3일 이내)", f"{s['due_soon']}개")
m4.metric("마감 지남", f"{s['overdue']}개", "확인 필요" if s["overdue"] else None, delta_color="inverse")

left, right = st.columns([3, 2])

# ---------- 팀원별 ----------
with left:
    st.subheader("팀원별 진행")
    rows = db.by_member(items)
    chart = pd.DataFrame({"완료": [r["done"] for r in rows], "남음": [r["total"] - r["done"] for r in rows]},
                         index=[r["member"] for r in rows])
    st.bar_chart(chart, color=["#2F5FD0", "#D6D0C3"], horizontal=True, height=260)

# ---------- 마감 임박 ----------
with right:
    st.subheader("⏰ 마감 임박 · 지남")
    due = db.due_list(items, today)
    if not due:
        st.success("3일 안에 마감인 미완료 할 일이 없어요.")
    for i in due:
        label = f"D+{-i['d_day']} 지남" if i["d_day"] < 0 else ("오늘 마감" if i["d_day"] == 0 else f"D-{i['d_day']}")
        color = "red" if i["d_day"] <= 0 else "orange"
        st.markdown(f":{color}[**{label}**] {i['task']} — {i.get('assignee', '미정')} ({i['due']})")

# ---------- 전체 할 일 + 상태 변경 ----------
st.subheader("전체 할 일")
st.caption("상태를 바꾸면 바로 저장돼요.")
table = pd.DataFrame([{
    "상태": i["status"],
    "할 일": i["task"],
    "담당": i.get("assignee") or "미정",
    "마감": i.get("due") or "미정",
    "회의": f"{i['meeting_date']} {i['meeting_title']}".strip(),
    "이슈": i.get("issue_url") or None,
} for i in items])
edited = st.data_editor(
    table, key="status_editor", hide_index=True, width="stretch", num_rows="fixed",
    disabled=["할 일", "담당", "마감", "회의", "이슈"],
    column_config={
        "상태": st.column_config.SelectboxColumn(options=storage.STATUSES, required=True),
        "이슈": st.column_config.LinkColumn(display_text="열기"),
    },
)
changed = False
for item, new_status in zip(items, edited["상태"]):
    if new_status != item["status"]:
        storage.update_action(item["meeting_id"], item["index"], status=new_status)
        changed = True
if changed:
    st.toast("상태를 저장했어요.")
    st.rerun()

# ---------- 다음 회의 ----------
st.subheader("🗓️ 다음 회의 준비")
a1, a2 = st.columns([3, 2])
with a1:
    st.markdown("**다음 회의 안건 제안** (미완료 할 일 · 담당 미정 먼저)")
    agenda = db.next_agenda(items)
    if not agenda:
        st.write("모든 할 일이 끝났어요 🎉")
    for i in agenda[:8]:
        who = i.get("assignee") or "미정"
        tag = " :orange[담당 정하기]" if who == "미정" else ""
        st.markdown(f"- {STATUS_ICON[i['status']]} {i['task']} — {who} · {i.get('due') or '마감 미정'}{tag}")
with a2:
    deadline = db.nearest_deadline(items, today)
    with st.container(border=True):
        if deadline:
            st.markdown(f"가장 가까운 마감: **{deadline:%m/%d}**")
            st.write("그 전에 한 번 모여서 점검하는 걸 추천해요.")
        else:
            st.write("다가오는 마감이 없어요.")
        if st.button("다음 회의 잡기 →", type="primary", width="stretch"):
            st.session_state["base_date"] = today
            st.session_state["deadline"] = deadline
            st.switch_page("views/schedule.py")

# ---------- 회의 이력 ----------
st.subheader("📚 회의 이력")
for m in reversed(meetings):
    acts = m.get("actions", [])
    done = sum(a.get("status") == "완료" for a in acts)
    with st.expander(f"{m.get('date', '')} · {m.get('title') or '제목 없음'} — 할 일 {done}/{len(acts)} 완료"):
        st.write(f"참석: {', '.join(m.get('attendees', []))}")
        if m.get("decisions"):
            st.markdown("**결정 사항**")
            for d in m["decisions"]:
                st.markdown(f"- {d['text']}")
        st.markdown("**할 일**")
        for a in acts:
            st.markdown(f"- {STATUS_ICON.get(a.get('status'), '⬜')} {a['task']} — {a.get('assignee', '미정')}")
        if st.button("이 회의 삭제", key=f"del_{m['id']}"):
            storage.delete_meeting(m["id"])
            st.rerun()
