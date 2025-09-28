import streamlit as st

st.set_page_config(page_title="Timesheet Calculator", page_icon="🗓️", layout="wide")

st.title("🗓️ Timesheet Calculator")

st.markdown("""
Welcome! Use the sidebar to navigate:

1. **Enter Timesheet** – Fill in daily entries (with Sick/Off/ADO toggles).
2. **Review Calculations** – View computed Unit, loadings, and totals.

💡 Tip: On iPhone, open in Safari → Share → *Add to Home Screen* for an app-like feel.
""")
