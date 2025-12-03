import os
import sys

import streamlit as st

# Ensure project root is importable when running `streamlit run app/app.py`
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Optional: show DB health if services.db exists
db_status = None
try:
    from services.db import check_connection  # type: ignore
    db_status = "OK" if check_connection() else "FAILED"
except Exception:
    db_status = "unknown"

PAGES = {
    "Home": "home",
    "Fixtures": "fixtures",
    "Teams": "teams",
    "Head-to-Head": "h2h",
    "Insights": "insights",
}


def render_header(title: str):
    st.set_page_config(page_title="Football Analytics", layout="wide")
    st.title(f"⚽ {title}")
    st.caption("Football Analytics Dashboard")
    with st.sidebar:
        st.markdown("### System")
        st.write(f"DB: {db_status}")


def page_home():
    render_header("Home")
    st.write("Welcome! Use the sidebar to navigate.")
    st.info("Tip: Configure your DB in `.env` and run tests with `pytest`.")


def page_fixtures():
    render_header("Fixtures")
    st.write("Upcoming fixtures and predictions will appear here.")
    st.warning("To be implemented: data query and table display.")


def page_teams():
    render_header("Teams")
    st.write("Team statistics, form, and performance metrics.")
    st.warning("To be implemented: filters, charts, and KPIs.")


def page_h2h():
    render_header("Head-to-Head")
    st.write("Compare two teams across historical matches.")
    st.warning("To be implemented: selectors and comparison charts.")


def page_insights():
    render_header("Insights")
    st.write("League-wide trends, anomalies, and calibration.")
    st.warning("To be implemented: dashboards and visualizations.")


def main():
    st.sidebar.markdown("## Navigation")
    selection = st.sidebar.radio("Go to:", list(PAGES.keys()), index=0)

    route = PAGES[selection]
    if route == "home":
        page_home()
    elif route == "fixtures":
        page_fixtures()
    elif route == "teams":
        page_teams()
    elif route == "h2h":
        page_h2h()
    elif route == "insights":
        page_insights()
    else:
        st.error("Page not found.")


if __name__ == "__main__":
    main()