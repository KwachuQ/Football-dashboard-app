import os
import sys
import streamlit as st

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(__file__)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

st.set_page_config(
    page_title="Football Analytics Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚽ Football Analytics Dashboard")
st.markdown("### Welcome to Football Analytics Dashboard")

st.info("👈 Use the sidebar to navigate between pages")

st.markdown("""
#### Available Pages:
- **Home** - League selection, data freshness, system health
- **Fixtures** - Upcoming matches with predictions
- **Teams** - Team statistics and analysis
- **Head to Head** - Compare teams
- **Insights** - League trends and anomalies
""")

st.markdown("---")

# Quick system status
col1, col2 = st.columns(2)

with col1:
    st.subheader("Database Status")
    try:
        from services.db import test_connection
        if test_connection():
            st.success("🟢 Connected")
        else:
            st.error("🔴 Disconnected")
    except Exception as e:
        st.error(f"🔴 Error: {e}")

with col2:
    st.subheader("Cache Status")
    try:
        from services.cache import CacheMonitor
        monitor = CacheMonitor()
        stats = monitor.get_stats()
        hit_rate = stats.get('hit_rate', 0.0)
        st.metric("Cache Hit Rate", f"{hit_rate:.1f}%")
    except Exception as e:
        st.warning("Cache monitoring unavailable")
