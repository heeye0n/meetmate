"""MeetMate 진입점. 실행: streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="MeetMate", page_icon="🗓️", layout="wide")

home = st.Page("views/home.py", title="홈", icon="🏠", default=True)
schedule = st.Page("views/schedule.py", title="약속 잡기", icon="🗓️")
minutes = st.Page("views/minutes.py", title="회의록 정리", icon="📝")
dashboard = st.Page("views/dashboard.py", title="대시보드", icon="📊")

st.navigation([home, schedule, minutes, dashboard]).run()
