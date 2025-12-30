import os
import sys
import streamlit as st
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



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

from services.cache import CacheWarmer

# Warm cache for common queries (don't block the main thread for too long)
# Since the queries are cached, this will only hit the DB once
CacheWarmer.warm_common_queries()

st.switch_page("pages/1_Home.py")


