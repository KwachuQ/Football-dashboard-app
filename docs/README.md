![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.6-336791.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.51-23BF00.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.3+-BC00BF.svg)
![Plotly](https://img.shields.io/badge/Plotly-6.5+-0089BF.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

# Football Analytics Dashboard

A Streamlit-based web application for visualizing football analytics, team performance metrics, match predictions, and league insights. This app connects to a PostgreSQL database populated by a data pipeline from my other project ([Football-data-pipeline](https://github.com/KwachuQ/Football-data-pipeline)) to provide real-time football statistics and predictions.

Check it out here: https://football-dashboard-app.streamlit.app/Home

## Features

- **Multi-League Support**: Analyze teams across different leagues (Ekstraklasa and more)
- **Upcoming Fixtures**: View upcoming matches with predictions, team form, and head-to-head records
- **Team Statistics**: Deep dive into attack, defense, possession, discipline, and BTTS metrics with radar charts and league percentile rankings
- **Head-to-Head Comparison**: Compare two teams side-by-side based on upcoming fixtures, including form, scoring profiles, and historical matchups
- **Performance Insights**: League-wide trends, anomalies, and performance tracking
- **Interactive Visualizations**: Charts and graphs powered by Plotly (line charts, pie charts, radar charts, bar charts)
- **Data Freshness Monitoring**: Track when data was last updated with database health checks
- **Caching & Performance**: Custom caching layer with cache warming, monitoring, and page load timing

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 17+** (with populated gold schema from data pipeline)
- **Docker & Docker Compose** (optional, for containerized deployment)
- **Git**

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Football-dashboard-app
```

### 2. Set Up Environment Variables

Copy the example environment file and configure your database credentials:

```bash
cp .env.example .env
```

Edit `.env` with your database configuration:

```env
# Required Database Credentials
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=your_db_name

# Optional (defaults provided)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# SQLAlchemy Connection Pool Settings
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=1800
SQLALCHEMY_ECHO=false
```

### 3. Install Dependencies

#### Option A: Using pip

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Option B: Using uv (faster)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 4. Verify Database Connection

Before running the app, verify your database connection:

```bash
pytest tests/test_db_connection.py -v
```

Expected output:
```
tests/test_db_connection.py::test_db_connection PASSED
```

### 5. Run the Application

```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`

## Project Structure

```
Football-dashboard-app/
├── app.py                        # Main Streamlit entry point (redirects to Home)
├── pages/
│   ├── 1_Home.py                 # Home page with league info, quick stats, DB status
│   ├── 2_Fixtures.py             # Upcoming fixtures with predictions and form
│   ├── 3_Teams.py                # Team statistics, form, radar charts, discipline
│   └── 4_Compare.py              # Head-to-head team comparison from fixtures
├── components/
│   └── __init__.py               # Reusable UI components (filters, charts, etc.)
├── config/
│   ├── settings.py               # Pydantic settings and configuration
│   └── league_config.yaml        # League and season configuration
├── services/
│   ├── __init__.py
│   ├── db.py                     # Database connection, engine, session management
│   ├── queries.py                # Parameterized SQL queries for all data access
│   └── cache.py                  # Caching utilities, cache warming, monitoring
├── src/
│   └── models/
│       ├── base.py               # SQLAlchemy declarative base
│       └── upcoming_fixtures.py  # UpcomingFixtures ORM model
├── tests/                        # Pytest test suite
├── scripts/
│   └── run_tests.py              # Test runner with custom configuration
├── static/                       # Static assets
├── docs/
│   ├── README.md                 # This file
├── aws_logs/                     # AWS deployment logs
├── .streamlit/
│   └── config.toml               # Streamlit configuration
├── .env.example                  # Environment variables template
├── .gitignore
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Python dependencies
└── LICENSE                       # MIT License
```

## Configuration

### Database Settings

The application uses Pydantic for settings validation. Configuration is loaded from environment variables or `.env` file. See [`config/settings.py`](config/settings.py) for all available options.

**Required Settings:**
- `POSTGRES_USER`: Database username
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_DB`: Database name

**Optional Settings (with defaults):**
- `POSTGRES_HOST`: Database host (default: `localhost`)
- `POSTGRES_PORT`: Database port (default: `5432`)
- `DB_POOL_SIZE`: Connection pool size (default: `5`)
- `DB_MAX_OVERFLOW`: Max overflow connections (default: `10`)
- `DB_POOL_RECYCLE`: Connection recycle time in seconds (default: `1800`)
- `SQLALCHEMY_ECHO`: Enable SQL query logging (default: `false`)

### League Configuration

League and season settings are managed via [`config/league_config.yaml`](config/league_config.yaml). The active league defaults to Ekstraklasa (Poland). The active season ID is stored in `st.session_state` and used across all pages.

### Database Requirements

The application expects the following gold mart tables in your PostgreSQL database:

- `mart_team_overview`
- `mart_team_form`
- `mart_team_attack`
- `mart_team_defense`
- `mart_team_possession`
- `mart_team_discipline`
- `mart_match_predictions`
- `mart_head_to_head`
- `mart_team_season_summary`
- `mart_upcoming_fixtures`

These tables should be populated by your data pipeline (you can find the pipeline here: https://github.com/KwachuQ/Football-data-pipeline).

## Pages

### Home (`pages/1_Home.py`)
- League and season information from config
- Quick statistics (total seasons, active league, upcoming fixtures count)
- Database connection health check
- Cache hit rate monitoring

### Fixtures (`pages/2_Fixtures.py`)
- Date range filter with configurable lookahead (default 45 days)
- Fixtures overview table with predictions, form indicators, and H2H records
- Detailed match expanders with prediction probabilities, fair odds, and recent form
- Bulk data loading for team forms and head-to-head records

### Teams (`pages/3_Teams.py`)
- Team selector with season filter
- Team header with position, matches played, points, PPG, and goal difference
- Tab-based layout:
  - **Overview**: Season summary stats, BTTS analysis, xG metrics
  - **Form**: Configurable form window (5/10/15/20 matches), points-per-match line chart, W/D/L pie chart
  - **Attack**: Goals scored, shots, accuracy with radar charts and league percentile tables
  - **Defense**: Goals conceded, tackles, clean sheets with radar charts
  - **Possession**: Pass completion, possession %, territory control
  - **Discipline**: Yellow/red cards, fouls, fair play rating
- Radar charts using `mplsoccer` with league average overlays
- Conditional formatting on stats tables (green/red for above/below average)

### Compare (`pages/4_Compare.py`)
- Fixture selector from upcoming matches (sidebar)
- **Head-to-Head Statistics**: Win/draw/loss record, stacked bar chart, goals and BTTS stats, over/under goal thresholds
- **Team Cards**: Side-by-side stats with form blocks (overall + home/away), tabbed stats tables with colored comparison
- **Current Form Comparison**: Points per game (home PPG vs away PPG), last 5 results breakdown by overall/home/away
- **Goals Scored Comparison**: Full-time and 1st half / 2nd half scored-per-game breakdowns
- **Goals Conceded Comparison**: Defensive analysis with conceded-per-game tables

## Testing

Run all tests:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=services --cov=config --cov-report=html
```

Run specific test file:

```bash
pytest tests/test_db_connection.py -v
```

Run tests excluding slow tests:

```bash
python scripts/run_tests.py
```

## Troubleshooting

### Database Connection Issues

**Problem:** `RuntimeError: Missing required database env vars`

**Solution:** Ensure all required environment variables are set in your `.env` file:
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

**Problem:** Database connection test fails

**Solution:**
1. Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
2. Check credentials are correct
3. Ensure database exists: `psql -U postgres -l`
4. Verify network connectivity and firewall rules

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'services'`

**Solution:** Ensure you're running from the project root. The [`app.py`](app.py) includes path configuration that adds the project root to `sys.path`:

```python
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Database layer powered by [SQLAlchemy](https://www.sqlalchemy.org/)
- Visualizations using [Plotly](https://plotly.com/) and [mplsoccer](https://mplsoccer.readthedocs.io/)
- Configuration management with [Pydantic](https://docs.pydantic.dev/)
---