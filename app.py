import os
import sys
import streamlit as st
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def get_show_timings_sidebar():
    """Lazy import show_timings_sidebar dla app.py"""
    from services.cache import show_timings_sidebar
    return show_timings_sidebar

show_timings_sidebar = get_show_timings_sidebar()

st.set_page_config(
    page_title="Football Analytics Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    [data-testid="stSidebarNav"] li:first-child {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

st.switch_page("pages/1_Home.py")


