## Plan: Streamlit Football Analytics App

### Executive Summary

Build a separate Streamlit app that connects to your Postgres (from the pipeline) to visualize upcoming fixtures with team form and performance. Use DBT gold marts as sources, support Ekstraklasa and configurable leagues, and surface freshness from incremental loads. The app will provide fixture exploration, head-to-head context, trendlines, and model-driven predictions with filters and export. Credentials and schemas are parameterized via environment variables and a lightweight settings file.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web App                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Home Page    │  │ Fixtures     │  │ Teams        │     │
│  │ - League Sel │  │ - Upcoming   │  │ - Form       │     │
│  │ - Freshness  │  │ - Predictions│  │ - Stats      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Head-to-Head │  │ Compare      │  │ Insights     │     │
│  │ - History    │  │ - Side-by-S. │  │ - Trends     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────────────────────────┤
│                  Application Layer                          │
│  ┌──────────────────────────────────────────────────┐      │
│  │  services/                                        │      │
│  │    - db.py (SQLAlchemy + connection pooling)    │      │
│  │    - cache.py (Streamlit caching strategies)     │      │
│  │    - queries.py (Parameterized SQL)              │      │
│  │  components/                                      │      │
│  │    - charts.py (Plotly/Altair visualizations)    │      │
│  │    - filters.py (Reusable filter widgets)        │      │
│  │    - metrics.py (KPI cards and indicators)       │      │
│  └──────────────────────────────────────────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │  PostgreSQL Database (Gold Schema)               │      │
│  │    - mart_team_overview                          │      │
│  │    - mart_team_form                              │      │
│  │    - mart_team_attack / defense / possession     │      │
│  │    - mart_team_discipline                        │      │
│  │    - mart_match_predictions                      │      │
│  │    - mart_head_to_head                           │      │
│  │    - mart_team_season_summary                    │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
           ▲
           │ Incremental Updates (Airflow DAGs)
           │
┌──────────┴────────────┐
│ Football Data Pipeline│
│ (Existing Project)    │
└───────────────────────┘
```

### Technology Stack

**Frontend & Framework**
- Streamlit 1.30+ (UI framework)
- Plotly 5.x (interactive charts)
- Altair (declarative visualizations)

**Backend & Data Access**
- SQLAlchemy 2.x (ORM and query builder)
- psycopg2-binary / asyncpg (Postgres drivers)
- pandas 2.x (data manipulation)

**Configuration & Deployment**
- python-dotenv (environment variables)
- pydantic (settings validation)
- Docker + docker-compose (containerization)
- Streamlit Cloud (optional hosted deployment)

**Testing & Quality**
- pytest (unit/integration tests)
- pytest-postgresql (test fixtures)
- pre-commit (code quality hooks)

**Testing & Quality**
- pytest (unit/integration tests)
- pytest-postgresql (test fixtures)
- pre-commit (code quality hooks)

---

## Implementation Roadmap

### Phase 1: Foundation & Setup (Week 1)
**Deliverables:**
- [ ] Project structure and repository initialization
- [ ] Database connection and configuration management
- [ ] Basic Streamlit app scaffold with navigation
- [ ] Environment setup and dependency management

**Tasks:**
1. Create separate repo structure: `app/`, `src/`, `pages/`, `components/`, `services/`, `config/`, `tests/`
2. Set up `requirements.txt` with core dependencies
3. Implement `services/db.py` with SQLAlchemy engine and connection pooling
4. Create `config/settings.py` using Pydantic for env var validation
5. Build basic `app.py` with sidebar navigation and page routing
6. Add `.env.example` template for configuration
7. Create `docker-compose.yml` for local development (app + postgres connection)
8. Write initial `README.md` with setup instructions

**Success Criteria:**
- App launches successfully and shows "Hello World" page
- Database connection established and tested
- Environment variables loaded correctly
- Docker container runs without errors

---

### Phase 2: Data Access Layer (Week 1-2)
**Deliverables:**
- [ ] SQLAlchemy models for all gold marts
- [ ] Parameterized query functions
- [ ] Caching strategy implementation
- [ ] Data freshness monitoring

**Tasks:**
1. Map CSV structures in `data/` to SQLAlchemy models (8 marts)
2. Implement `services/queries.py` with functions:
   - `get_upcoming_fixtures(league_id, days_ahead, limit)`
   - `get_team_form(team_id, last_n_matches)`
   - `get_team_stats(team_id, stat_type)` (attack/defense/possession/discipline)
   - `get_head_to_head(team1_id, team2_id, limit)`
   - `get_match_predictions(match_ids)`
   - `get_league_standings(league_id, season)`
   - `get_data_freshness()` (max updated_at per mart)
3. Add `services/cache.py` with caching decorators:
   - `@st.cache_data(ttl=600)` for query results
   - `@st.cache_resource` for DB engine
   - Cache invalidation utilities
4. Create `services/transforms.py` for data enrichment:
   - Rolling averages calculation
   - Home/away splits
   - Form indicators (W/D/L sequences)
   - Strength of schedule adjustments

**Success Criteria:**
- All queries return expected data types
- Cache hit rate > 80% on repeated queries
- Query response time < 2s for typical requests
- Freshness indicators accurate within 1 minute

---

### Phase 3: Core UI Pages (Week 2-3)
**Deliverables:**
- [ ] Home page with league selection and freshness dashboard
- [ ] Fixtures page with upcoming matches and predictions
- [ ] Teams page with comprehensive statistics
- [ ] Reusable UI components library

**Tasks:**

**Home Page (`pages/1_🏠_Home.py`)**
1. League selector dropdown (from `league_config.yaml`)
2. Data freshness dashboard (last update time per mart)
3. Quick stats cards (total teams, upcoming fixtures count, last predictions run)
4. System health indicators (DB status, cache size, error count)

**Fixtures Page (`pages/2_📅_Fixtures.py`)**
1. Date range filter (default: next 7 days)
2. League/competition filter
3. Fixtures table with columns:
   - Date/time, Home team, Away team, Venue
   - Predicted outcome (from mart_match_predictions)
   - Form indicators (last 5 matches W/D/L)
   - Head-to-head record
4. Click-to-expand match details (team stats comparison, prediction confidence)
5. Export to CSV button

**Teams Page (`pages/3_⚽_Teams.py`)**
1. Team selector (autocomplete search)
2. Tab-based layout:
   - **Overview**: Season summary stats, league position, goals for/against
   - **Form**: Last N matches chart (line graph), win/draw/loss distribution
   - **Attack**: Goals scored, shots, accuracy, expected goals (if available)
   - **Defense**: Goals conceded, tackles, clearances, clean sheets
   - **Possession**: Pass completion %, possession %, territory control
   - **Discipline**: Yellow/red cards, fouls committed/received
3. Time period selector (last 5/10/20 matches, or date range)
4. Home vs Away performance toggle

**Reusable Components (`components/`)**
1. `filters.py`: LeagueFilter, DateRangeFilter, TeamSelector, MatchCountSlider
2. `metrics.py`: KPICard, TrendIndicator, FreshnessBadge, WinRateGauge
3. `tables.py`: SortableDataFrame, ConditionalFormatter, ExportButton
4. `layout.py`: PageHeader, Sidebar, Footer

**Success Criteria:**
- All pages load in < 3s with sample data
- Filters update visualizations reactively
- Navigation between pages preserves state
- Mobile-responsive layout (min width 768px)

---

### Phase 4: Advanced Visualizations (Week 3-4)
**Deliverables:**
- [ ] Interactive charts for all key metrics
- [ ] Head-to-head comparison page
- [ ] Team comparison tool
- [ ] Insights and trends page

**Tasks:**

**Charts Library (`components/charts.py`)**
1. **Form Chart**: Line graph showing points per match over time, with trend line
2. **Performance Radar**: Multi-axis radar for attack/defense/possession/discipline (normalized 0-100)
3. **Attack vs Defense Scatter**: All teams plotted by goals scored vs conceded, with quadrant labels
4. **Possession Heatmap**: Match-by-match possession % with color gradient
5. **Discipline Timeline**: Stacked bar chart of yellow/red cards over time
6. **Prediction Calibration**: Actual vs predicted outcomes distribution
7. **Form Streaks**: Horizontal bar chart showing current W/D/L sequences
8. **Goal Distribution**: Histogram of goals scored/conceded by match period (1H vs 2H)

**Head-to-Head Page (`pages/4_🤝_Head_to_Head.py`)**
1. Two-team selector (Team A vs Team B)
2. Historical record summary (wins/draws/losses, goals for/against)
3. Last 10 meetings table with scores and dates
4. Head-to-head trends chart (rolling form when playing each other)
5. Venue analysis (home/away/neutral record)
6. Goal timing patterns (when teams score vs each other)

**Compare Page (`pages/5_🔄_Compare.py`)**
1. Multi-team selector (2-4 teams)
2. Side-by-side stat comparison table
3. Synchronized radar charts for all selected teams
4. Relative strength indicators (better/worse/similar badges)
5. Form convergence chart (trending towards similar form or diverging)

**Insights Page (`pages/6_📊_Insights.py`)**
1. League-wide insights:
   - Form leaders and worst performers (last 5 matches)
   - Biggest overperformers vs predictions
   - Most improved teams (month-over-month)
   - Attack/defense efficiency leaders
2. Anomaly detection:
   - Teams with unusual form changes
   - Unexpected results (large prediction errors)
   - Statistical outliers (possession/shots but few goals)
3. Trend analysis:
   - League average metrics over time
   - Home advantage trends
   - Disciplinary trends (cards per match)

**Success Criteria:**
- All charts render in < 1s with cached data
- Interactive tooltips show detailed values
- Charts downloadable as PNG/SVG
- Colorblind-friendly palettes used
- Insights auto-refresh with latest data

---

### Phase 5: Predictions & Intelligence (Week 4)
**Deliverables:**
- [ ] Match prediction display with confidence intervals
- [ ] Prediction accuracy tracking
- [ ] Feature importance explanations
- [ ] Betting odds integration (optional)

**Tasks:**
1. **Prediction Display** (`components/predictions.py`):
   - Outcome probabilities (home win / draw / away win)
   - Confidence score and uncertainty range
   - Key factors influencing prediction (top 5 features)
   - Historical accuracy for similar fixtures
2. **Accuracy Dashboard** (in Insights page):
   - Brier score and log loss metrics
   - Calibration plot (predicted vs actual probabilities)
   - Accuracy by league, team, and prediction confidence
   - Error analysis (over/under confident scenarios)
3. **Explainability** (`services/explainer.py`):
   - Feature contribution breakdown (SHAP-style visualization)
   - "Team X favored because..." natural language summary
   - Scenario analysis ("What if Team A's form improves?")
4. **Odds Comparison** (optional):
   - Display bookmaker odds if available
   - Value bets (predictions significantly different from odds)
   - Kelly criterion stake sizing calculator

**Success Criteria:**
- Predictions match those in `mart_match_predictions`
- Accuracy metrics verifiable against historical data
- Explanations clear and actionable for non-technical users

---

### Phase 6: Multi-League & Configuration (Week 5)
**Deliverables:**
- [ ] League configuration management
- [ ] Dynamic league switching
- [ ] Season comparison tools
- [ ] Custom metric definitions

**Tasks:**
1. Parse `config/league_config.yaml` to populate league selector
2. Implement league-specific queries with `league_id` parameter
3. Add season selector (current, previous, historical)
4. Create season-over-season comparison view
5. Allow users to define custom metrics (weighted form scores, composite ratings)
6. Support league-specific business rules (e.g., playoff formats, relegation zones)
7. Add league metadata display (country, tier, teams count)

**Success Criteria:**
- Switching leagues updates all pages without errors
- Season data correctly filtered and labeled
- Custom metrics persist in user session
- Ekstraklasa set as default league

---

### Phase 7: Performance & Optimization (Week 5)
**Deliverables:**
- [ ] Query optimization and indexing
- [ ] Advanced caching strategies
- [ ] Lazy loading for heavy visualizations
- [ ] Performance monitoring

**Tasks:**
1. Add database indexes on frequently queried columns:
   - `league_id`, `team_id`, `match_date`, `season`
   - Composite indexes for common joins
2. Implement query result pagination (limit 100, then "Load More")
3. Add server-side filtering for large datasets
4. Lazy load charts (render only visible tabs/pages)
5. Use `st.experimental_memo` for expensive computations
6. Add performance timing decorators to track slow queries
7. Implement graceful degradation (show cached/partial data if DB slow)
8. Set up pre-aggregation materialized views for heavy stats (if needed)

**Success Criteria:**
- Page load time < 2s for 95th percentile
- Database query time < 500ms for 90th percentile
- Cache hit rate > 85%
- App remains responsive with 10+ concurrent users

---

### Phase 8: Testing & Quality Assurance (Week 6)
**Deliverables:**
- [ ] Unit tests for all services
- [ ] Integration tests for database queries
- [ ] UI snapshot tests
- [ ] Test data fixtures

**Tasks:**
1. Create `tests/` structure:
   - `tests/unit/` for services, transforms, utilities
   - `tests/integration/` for DB queries and API calls
   - `tests/fixtures/` for sample data
2. Write unit tests (`pytest`):
   - `test_db.py`: Connection, queries, error handling
   - `test_transforms.py`: Form calculations, rolling averages
   - `test_cache.py`: Cache hit/miss, invalidation
   - `test_queries.py`: SQL generation, parameter binding
3. Integration tests with `pytest-postgresql`:
   - Seed test database with sample gold marts
   - Test end-to-end query flows
   - Verify data freshness logic
4. UI tests (optional, using `streamlit.testing`):
   - Page rendering without errors
   - Filter interactions
   - Chart data accuracy
5. Add `docker-compose.test.yml` for isolated test environment
6. Set up CI/CD pipeline (GitHub Actions):
   - Run tests on every PR
   - Code coverage reporting (target: > 80%)
   - Linting and formatting checks

**Success Criteria:**
- Test coverage > 80% for services layer
- All tests pass in CI environment
- No regressions introduced in new features
- Test suite runs in < 2 minutes

---

### Phase 9: Deployment & DevOps (Week 6)
**Deliverables:**
- [ ] Dockerized application
- [ ] Production-ready docker-compose
- [ ] Deployment documentation
- [ ] Monitoring and logging

**Tasks:**
1. Create `Dockerfile` for Streamlit app:
   - Multi-stage build (dependencies, app code)
   - Non-root user for security
   - Health check endpoint
2. Update `docker-compose.yml` for production:
   - Read-only Postgres connection
   - Environment variable injection
   - Restart policies
   - Resource limits (CPU, memory)
3. Add `Makefile` with common commands:
   - `make build`, `make run`, `make test`, `make deploy`
4. Set up logging:
   - Structured logging (JSON format)
   - Log levels (DEBUG, INFO, WARNING, ERROR)
   - Log rotation and retention
5. Add monitoring (optional):
   - Prometheus metrics endpoint
   - Grafana dashboard for app metrics
   - Alerting for errors and downtime
6. Write deployment guides:
   - Local development setup
   - Docker deployment
   - Streamlit Cloud deployment
   - Cloud providers (AWS, GCP, Azure)
7. Security hardening:
   - Read-only DB user with minimal permissions
   - Secrets management (not in git)
   - Rate limiting for refresh operations
   - HTTPS enforcement in production

**Success Criteria:**
- App deploys with single command (`docker-compose up`)
- Zero-downtime updates possible
- Logs accessible and searchable
- Passes basic security scan (no secrets in images)

---

### Phase 10: Documentation & Launch (Week 7)
**Deliverables:**
- [ ] Comprehensive README
- [ ] User guide and tutorials
- [ ] API/schema documentation
- [ ] Contribution guidelines

**Tasks:**
1. **README.md** sections:
   - Project overview and goals
   - Features list with screenshots
   - Quick start (5-minute setup)
   - Environment variables reference
   - Troubleshooting FAQ
2. **User Guide** (`docs/USER_GUIDE.md`):
   - Navigating the app
   - Understanding predictions
   - Interpreting visualizations
   - Exporting data
   - Custom scenarios
3. **Developer Guide** (`docs/DEVELOPER_GUIDE.md`):
   - Architecture overview
   - Code structure
   - Adding new pages/charts
   - Database schema reference
   - Testing guidelines
4. **Schema Documentation** (`docs/SCHEMA.md`):
   - Gold mart table definitions
   - Column descriptions and data types
   - Relationships and foreign keys
   - Update frequency and sources
5. **Changelog** (`CHANGELOG.md`):
   - Version history
   - Feature releases
   - Bug fixes and improvements
6. Create demo video or GIF walkthrough
7. Prepare launch checklist:
   - Performance benchmarks met
   - All tests passing
   - Documentation complete
   - Security review done
   - User acceptance testing completed

**Success Criteria:**
- New user can set up app in < 10 minutes following README
- All features documented with examples
- Zero critical bugs in launch version
- Positive feedback from 3+ alpha testers

---

## Project Structure
1. Define app requirements and data contracts using `docs/README.md`, `config/league_config.yaml`, and gold mart CSVs in `data/` as proxies for table shapes.
2. Map DB sources: outline target schemas/tables for `mart_team_*`, `mart_match_predictions`, `mart_head_to_head`; confirm Postgres connection via `docker/docker-compose.yml` and `postgres/init/`.
3. Create separate repo structure: `app/`, `src/`, `pages/`, `components/`, `services/db.py`, `services/cache.py`, `charts/`, `config/settings.toml`, `requirements.txt`, `README.md`.
4. Implement DB connectivity: in `services/db.py` use `psycopg`/`asyncpg` with env vars (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SCHEMA`), plus `sqlalchemy` models for marts.
5. Build data access layer: parameterized queries for fixtures, team form windows, head-to-head, predictions; add freshness checks using Airflow/DBT run timestamps if available.
6. Design UI pages: Home (league selection, freshness), Fixtures (upcoming matches, filters, odds/predictions), Teams (form, attack/defense, possession, discipline), Head-to-Head (history and context), Compare (two-team side-by-side), Insights (trendlines and anomalies).
7. Create visualizations: line charts for form over last N matches, bar/radar for performance metrics, scatter for attack vs defense, heatmaps for possession/discipline, tables with conditional formatting for fixtures.
8. Add feature engineering in-app: configurable form window (e.g., last 5/10 matches), strength-of-schedule adjustment, home/away splits, rolling averages.
9. Build prediction overlays: display `mart_match_predictions` with confidence, calibration summary, and deltas vs bookmaker benchmarks (optional if available).
10. Implement caching: `st.cache_data` for query results keyed by league/date; `st.cache_resource` for DB engine; add manual refresh button reflecting incremental pipeline cadence.
11. Add multi-league support: read supported leagues from `config/league_config.yaml`; default to Ekstraklasa; scope queries by league_id/season.
12. Provide export: CSV/PNG downloads for filtered tables and charts; permalink query state via URL params.
13. Observability: show data freshness (max `updated_at` per mart), last Airflow/DBT run timestamps, and row counts; error banners when stale/empty.
14. Testing: unit tests for queries and transformations; snapshot tests for chart data; a mock Postgres via `docker-compose.test.yml`.
15. Deployment: Dockerize the app; compose with Postgres network or read-only access; add `Makefile` scripts and `README` quickstart; optional Streamlit Cloud with managed Postgres.
16. Security and privacy: read-only DB user; parameterized queries; rate-limit refresh; secrets via `.env` and platform secrets; no PII.
17. Performance: pagination for tables, server-side filters, index suggestions for frequently queried columns, pre-aggregations for heavy stats.
18. Roadmap: add model explainability, expected goals (xG) if data available, match previews, alerting for notable form changes.

**Success Criteria:**
- New user can set up app in < 10 minutes following README
- All features documented with examples
- Zero critical bugs in launch version
- Positive feedback from 3+ alpha testers

---

## Project Structure

```
football-analytics-app/
├── .env.example                 # Environment variables template
├── .gitignore
├── .pre-commit-config.yaml      # Code quality hooks
├── docker-compose.yml           # Local development environment
├── docker-compose.test.yml      # Testing environment
├── Dockerfile                   # Production container
├── Makefile                     # Build and run commands
├── README.md                    # Main documentation
├── requirements.txt             # Python dependencies
├── setup.py                     # Package configuration (optional)
│
├── app.py                       # Main Streamlit entry point
│
├── config/
│   ├── __init__.py
│   ├── settings.py              # Pydantic settings models
│   ├── leagues.yaml             # League configurations (copied from pipeline)
│   └── logging.yaml             # Logging configuration
│
├── src/
│   ├── __init__.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── db.py                # Database connection and engine
│   │   ├── queries.py           # Parameterized SQL queries
│   │   ├── cache.py             # Caching utilities and decorators
│   │   ├── transforms.py        # Data transformation functions
│   │   └── explainer.py         # Prediction explanations
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py              # SQLAlchemy base
│   │   ├── team.py              # Team-related models
│   │   ├── match.py             # Match and fixture models
│   │   └── prediction.py        # Prediction models
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── charts.py            # Plotly/Altair chart functions
│   │   ├── filters.py           # Reusable filter widgets
│   │   ├── metrics.py           # KPI cards and metrics
│   │   ├── tables.py            # Enhanced dataframe displays
│   │   ├── predictions.py       # Prediction display components
│   │   └── layout.py            # Layout helpers
│   │
│   └── utils/
│       ├── __init__.py
│       ├── formatters.py        # Data formatting utilities
│       ├── validators.py        # Input validation
│       └── constants.py         # App-wide constants
│
├── pages/
│   ├── 1_🏠_Home.py             # Home page with overview
│   ├── 2_📅_Fixtures.py         # Upcoming fixtures and predictions
│   ├── 3_⚽_Teams.py             # Team statistics and analysis
│   ├── 4_🤝_Head_to_Head.py     # Head-to-head comparison
│   ├── 5_🔄_Compare.py          # Multi-team comparison
│   └── 6_📊_Insights.py         # League insights and trends
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   │
│   ├── unit/
│   │   ├── test_db.py
│   │   ├── test_transforms.py
│   │   ├── test_cache.py
│   │   └── test_queries.py
│   │
│   ├── integration/
│   │   ├── test_end_to_end.py
│   │   └── test_database_queries.py
│   │
│   └── fixtures/
│       ├── sample_data.sql      # Test database seed
│       └── mock_responses.json  # Mock API/DB responses
│
├── docs/
│   ├── USER_GUIDE.md            # End-user documentation
│   ├── DEVELOPER_GUIDE.md       # Developer documentation
│   ├── SCHEMA.md                # Database schema reference
│   ├── DEPLOYMENT.md            # Deployment instructions
│   └── screenshots/             # App screenshots for docs
│
├── scripts/
│   ├── seed_test_data.py        # Generate test data
│   ├── verify_db_connection.py # Database connectivity check
│   └── export_data.py           # Data export utilities
│
└── .streamlit/
    ├── config.toml              # Streamlit configuration
    └── secrets.toml.example     # Secrets template (not in git)
```

---

---

## Detailed Implementation Tasks

### Step-by-Step Breakdown

#### 1. Define App Requirements and Data Contracts
- Review `docs/README.md` from pipeline for context on data sources and transformations
- Analyze `config/league_config.yaml` to understand supported leagues and their metadata
- Inspect CSV files in `data/` folder to map column names, types, and relationships:
  - `mart_team_overview`: Team identifiers, league, season, basic stats
  - `mart_team_form`: Win/draw/loss records, points, recent match results
  - `mart_team_attack/defense/possession/discipline`: Detailed performance metrics
  - `mart_match_predictions`: Fixture predictions with probabilities
  - `mart_head_to_head`: Historical matchup data
  - `mart_team_season_summary`: Aggregated season metrics
- Document expected data types, nullable fields, and foreign key relationships
- Define data freshness SLA (e.g., "updated within 6 hours of match completion")

#### 2. Map Database Sources
- Examine `docker/docker-compose.yml` for Postgres service configuration:
  - Default host, port, database name, user credentials
- Check `postgres/init/` for schema creation scripts and initial data
- Verify `dbt/models/` to confirm gold mart table names and structures
- Review `dbt_project.yml` for schema naming conventions (e.g., `gold`, `analytics`)
- Test connection to Postgres from pipeline environment
- Document connection string format: `postgresql://user:pass@host:port/dbname`

#### 3. Create Separate Repository Structure
- Initialize new git repository: `football-analytics-app`
- Create directory structure as outlined in "Project Structure" section
- Set up `.gitignore` for Python (venv, __pycache__, .env, etc.)
- Add `README.md` with placeholder content
- Initialize `requirements.txt` with base dependencies:
  ```
  streamlit>=1.30.0
  sqlalchemy>=2.0.0
  psycopg2-binary>=2.9.0
  pandas>=2.0.0
  plotly>=5.18.0
  altair>=5.2.0
  python-dotenv>=1.0.0
  pydantic>=2.5.0
  pydantic-settings>=2.1.0
  ```

#### 4. Implement Database Connectivity
- Create `config/settings.py` with Pydantic models:
  ```python
  from pydantic_settings import BaseSettings
  
  class DatabaseSettings(BaseSettings):
      db_host: str
      db_port: int = 5432
      db_name: str
      db_user: str
      db_password: str
      db_schema: str = "gold"
      
      class Config:
          env_file = ".env"
  ```
- Implement `services/db.py`:
  - SQLAlchemy engine creation with connection pooling
  - Session factory with context manager
  - Health check function (`test_connection()`)
  - Graceful error handling and retry logic
- Create `.env.example` with all required variables
- Add connection string builder utility

#### 5. Build Data Access Layer
- Define SQLAlchemy models in `src/models/`:
  - `team.py`: TeamOverview, TeamForm, TeamSeasonSummary
  - `match.py`: MatchPrediction, HeadToHead
  - Use declarative base and reflect existing tables or define explicitly
- Implement query functions in `services/queries.py`:
  - Use parameterized queries with SQLAlchemy ORM or Core
  - Add type hints for all parameters and return values
  - Include docstrings with example usage
  - Handle edge cases (empty results, invalid IDs)
- Create data transformation functions in `services/transforms.py`:
  - `calculate_rolling_average(df, column, window)`
  - `compute_form_score(results_list, weights)`
  - `split_home_away(df, team_id)`
  - `normalize_metrics(df, columns, scale=100)`
- Add freshness monitoring:
  - Query for `max(updated_at)` per mart table
  - Compare against current timestamp
  - Flag stale data (> 24 hours old)

#### 6. Design UI Pages (Core Structure)
- Create `app.py` as main entry point:
  - Set page config (title, icon, layout, sidebar state)
  - Initialize session state for shared filters
  - Render sidebar with navigation and global filters
  - Display data freshness banner if stale
- Implement page routing using Streamlit's multi-page structure
- Add common page template with header, footer, and error boundaries
- Create `components/layout.py` with reusable layout functions

#### 7. Create Visualizations
- Implement chart functions in `components/charts.py`:
  - Use Plotly for interactive charts (hover, zoom, pan)
  - Use Altair for declarative, simple charts
  - Ensure consistent color schemes (team colors where applicable)
  - Add download buttons (PNG, SVG) to all charts
  - Implement responsive sizing based on container width
- Chart types to implement:
  - Line charts: Form trends over time
  - Bar charts: Attack/defense metrics comparison
  - Radar charts: Multi-dimensional team profiles
  - Scatter plots: Attack vs defense league-wide
  - Heatmaps: Possession or discipline patterns
  - Tables: Fixtures list with conditional formatting
- Add chart configuration options (toggle data labels, legend position, etc.)

#### 8. Add Feature Engineering
- Implement configurable form window:
  - Slider to select last N matches (5, 10, 15, 20, season)
  - Recalculate all metrics based on selected window
  - Show comparison to season-long averages
- Add strength of schedule adjustment:
  - Weight recent matches by opponent quality (league position, rating)
  - Display "true form" vs "raw form"
- Create home/away split analysis:
  - Filter all metrics by home or away games only
  - Show differential (home advantage/disadvantage)
- Implement rolling averages:
  - Goals per match (rolling 5, 10 matches)
  - Points per match
  - Discipline (cards per match)

#### 9. Build Prediction Overlays
- Display predictions from `mart_match_predictions`:
  - Home win / Draw / Away win probabilities
  - Most likely score (if available)
  - Confidence interval or uncertainty measure
- Show calibration metrics:
  - How often 70% predictions come true
  - Brier score for overall accuracy
  - Expected value of predictions vs actual outcomes
- Add comparison to benchmarks:
  - Bookmaker odds (if available via API or manual entry)
  - Simple baseline model (e.g., home win probability = 45%)
  - Highlight value opportunities (model disagrees with market)
- Include disclaimers about prediction limitations and responsible use

#### 10. Implement Caching
- Add `@st.cache_data(ttl=600)` to query functions:
  - Cache keyed by query parameters (league, date, team IDs)
  - TTL of 10 minutes for incremental data
  - Longer TTL (1 hour) for historical/static data
- Use `@st.cache_resource` for DB engine (singleton pattern)
- Implement cache warming on app startup for common queries
- Add manual "Refresh Data" button that clears relevant cache entries
- Monitor cache performance with hit rate metrics

#### 11. Add Multi-League Support
- Parse `config/league_config.yaml` to extract league metadata:
  - League ID, name, country, tier, active status
- Populate league selector dropdown in sidebar
- Store selected league in `st.session_state`
- Filter all queries by selected league ID
- Default to Ekstraklasa (league ID from config)
- Add league-specific context:
  - Display league logo/flag
  - Show league-specific stats (teams count, rounds played)
  - Highlight relegation zone and European qualification spots

#### 12. Provide Export Functionality
- Add CSV export for all tables:
  - "Download as CSV" button below each dataframe
  - Include filtered/sorted data as displayed
  - Filename format: `{page}_{league}_{date}.csv`
- Add PNG/SVG export for charts:
  - Plotly's built-in download modebar
  - Custom download button with higher resolution (300 DPI)
- Implement URL parameter state persistence:
  - Encode filters in query string (`?league=ekstraklasa&team=123`)
  - Parse on page load to restore state
  - "Copy shareable link" button

#### 13. Observability and Data Quality
- Create data freshness dashboard on Home page:
  - Table showing each mart with last update timestamp
  - Visual indicator (green/yellow/red) based on age
  - Link to Airflow DAG run history (if accessible)
- Display row counts and data coverage:
  - "X teams tracked, Y fixtures upcoming, Z predictions generated"
  - Percentage of matches with predictions
  - Percentage of teams with complete stats
- Add error banners:
  - When data is stale (> 24 hours old)
  - When DB connection fails (with retry button)
  - When query returns empty results (with helpful message)
- Log application errors to file and/or external service

#### 14. Testing
- Write unit tests for all services:
  - Mock database with `pytest-postgresql` or SQLite
  - Test query functions with sample data
  - Verify caching behavior (hit/miss scenarios)
  - Test transform functions with edge cases (empty data, single row, etc.)
- Create integration tests:
  - Seed test database with realistic sample data
  - Run end-to-end query flows
  - Verify data consistency across related tables
- Add UI tests (optional):
  - Use `streamlit.testing.v1` (if available)
  - Test page rendering without errors
  - Verify filter interactions update state correctly
- Set up CI pipeline (GitHub Actions):
  - Run tests on every push and PR
  - Generate code coverage report
  - Lint with `ruff` or `flake8`
  - Format check with `black`

#### 15. Deployment
- Create `Dockerfile`:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  EXPOSE 8501
  HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1
  CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
  ```
- Create production `docker-compose.yml`:
  - Link to existing Postgres service or use connection string
  - Mount `.env` for secrets
  - Set resource limits (CPU: 1, Memory: 2GB)
  - Add restart policy: `unless-stopped`
- Write deployment guides:
  - **Local**: `docker-compose up -d`
  - **Streamlit Cloud**: Connect GitHub repo, set secrets in dashboard
  - **Cloud VM**: Docker installation, firewall rules, reverse proxy (Nginx)
- Security hardening:
  - Create read-only DB user with SELECT-only permissions on gold schema
  - Use secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)
  - Enable HTTPS with Let's Encrypt or cloud provider certificates
  - Add rate limiting on refresh operations to prevent abuse
  - Implement session-based authentication if needed (Streamlit supports this)

#### 16. Security and Privacy
- Database access control:
  - Create dedicated read-only user: `CREATE USER streamlit_ro WITH PASSWORD '...'`
  - Grant SELECT only: `GRANT SELECT ON ALL TABLES IN SCHEMA gold TO streamlit_ro`
  - Revoke write permissions explicitly
- Secure secrets:
  - Never commit `.env` or `secrets.toml` to git
  - Use environment variables in production
  - Rotate DB passwords periodically
- Input validation:
  - Sanitize all user inputs (team IDs, league names, date ranges)
  - Use parameterized queries to prevent SQL injection
  - Validate league/team IDs against whitelist from config
- Rate limiting:
  - Limit refresh button to once per minute per user
  - Track API/DB calls per session
  - Throttle expensive queries (full table scans)
- Privacy:
  - Ensure no PII (personally identifiable information) in data
  - Log only anonymized user actions (no IP addresses, user agents)
  - Add privacy policy page if collecting any user data

#### 17. Performance Optimization
- Database indexing recommendations:
  - Create indexes on: `league_id`, `team_id`, `match_date`, `season`
  - Composite index on `(league_id, team_id, match_date)` for common joins
  - Index on `updated_at` for freshness queries
  - Analyze query plans with `EXPLAIN` and optimize slow queries
- Implement pagination:
  - Limit initial table display to 50-100 rows
  - "Load more" or "Show all" button for remaining data
  - Use `LIMIT` and `OFFSET` in SQL queries
- Server-side filtering:
  - Apply filters in SQL `WHERE` clauses, not pandas
  - Push down aggregations to database when possible
- Lazy loading:
  - Load charts only for active tab
  - Defer heavy computations until user navigates to page
- Pre-aggregations:
  - Create materialized views for expensive aggregations
  - Refresh via scheduled job aligned with pipeline updates
- Connection pooling:
  - Use SQLAlchemy pool with max 10 connections
  - Set pool recycle to 3600 seconds to handle stale connections

#### 18. Future Enhancements (Roadmap)
- **Model Explainability**: SHAP values or feature importance charts for predictions
- **Expected Goals (xG)**: If data available, display xG vs actual goals
- **Match Previews**: Automated narrative summaries for upcoming fixtures
- **Alerts**: Email/Slack notifications for notable form changes or prediction updates
- **Betting Tools**: Kelly criterion, bankroll management, bet tracking
- **User Accounts**: Save favorite teams, custom dashboards, personalized alerts
- **Mobile App**: Progressive Web App (PWA) or native mobile version
- **API**: Expose read-only API for external integrations
- **Social Sharing**: Share charts and insights on Twitter, Facebook
- **Multi-Language**: i18n support for Polish, English, etc.

---

## Key Considerations and Risks

### Data Quality and Freshness
**Challenge**: Pipeline may have delays or data gaps  
**Mitigation**:
- Display clear freshness indicators on all pages
- Implement graceful degradation (show cached data with staleness warning)
- Add data quality checks (e.g., fixture count matches expected based on league schedule)
- Provide contact/feedback mechanism for users to report data issues

### Postgres Schema Changes
**Challenge**: DBT models may evolve, breaking app queries  
**Mitigation**:
- Use SQLAlchemy ORM to abstract schema changes where possible
- Implement schema version checking (compare expected vs actual columns)
- Add integration tests that fail if schema changes unexpectedly
- Document schema dependencies and versioning strategy
- Consider using Alembic for app-side schema migrations if needed

### Performance at Scale
**Challenge**: App may slow down with many concurrent users or large datasets  
**Mitigation**:
- Implement aggressive caching (10-minute TTL for most queries)
- Use read replicas for Postgres if available
- Optimize SQL queries with proper indexes and query plans
- Consider serverless deployment (AWS Fargate, Cloud Run) for auto-scaling
- Monitor performance with APM tools (New Relic, Datadog)

### Prediction Model Transparency
**Challenge**: Users may misinterpret or over-rely on predictions  
**Mitigation**:
- Prominent disclaimers about prediction limitations
- Display confidence intervals and historical accuracy
- Show feature importance to explain predictions
- Avoid language like "guaranteed" or "certain"
- Link to methodology documentation

### Security and Access Control
**Challenge**: Database contains potentially sensitive or proprietary data  
**Mitigation**:
- Read-only DB user with minimal permissions
- No write operations from Streamlit app
- Optional authentication layer (Streamlit auth, OAuth)
- Audit logging of all DB queries
- Regular security reviews and updates

### Multi-League Configuration
**Challenge**: Different leagues have different rules, schedules, data availability  
**Mitigation**:
- Flexible league config with metadata (season format, playoff structure)
- Conditional logic based on league properties
- Default behavior for missing data (e.g., if xG not available, hide that section)
- Thorough testing with Ekstraklasa and at least one other league

---

## Success Metrics

### Technical Metrics
- [ ] Page load time < 2s (95th percentile)
- [ ] Database query time < 500ms (90th percentile)
- [ ] Cache hit rate > 85%
- [ ] Test coverage > 80%
- [ ] Zero critical security vulnerabilities
- [ ] 99.5% uptime (excluding planned maintenance)

### User Experience Metrics
- [ ] Setup time < 10 minutes for new users
- [ ] Average session duration > 5 minutes
- [ ] Pages per session > 3
- [ ] User satisfaction score > 4/5
- [ ] Feature adoption rate > 60% (at least 3 pages visited per user)

### Data Quality Metrics
- [ ] Data freshness < 6 hours (95th percentile)
- [ ] Prediction accuracy (Brier score) < 0.25
- [ ] Zero data integrity errors (mismatched IDs, orphan records)
- [ ] Complete coverage for Ekstraklasa (all teams, all fixtures)

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 1. Foundation & Setup | Week 1 | Project structure, DB connection, basic UI |
| 2. Data Access Layer | Week 1-2 | SQLAlchemy models, queries, caching |
| 3. Core UI Pages | Week 2-3 | Home, Fixtures, Teams pages |
| 4. Advanced Visualizations | Week 3-4 | Charts, Head-to-Head, Compare, Insights |
| 5. Predictions & Intelligence | Week 4 | Prediction display, accuracy tracking |
| 6. Multi-League & Configuration | Week 5 | League switching, season comparison |
| 7. Performance & Optimization | Week 5 | Indexing, caching, lazy loading |
| 8. Testing & Quality Assurance | Week 6 | Unit/integration tests, CI/CD |
| 9. Deployment & DevOps | Week 6 | Docker, deployment guides, monitoring |
| 10. Documentation & Launch | Week 7 | README, user guide, demo, launch |

**Total Estimated Duration**: 7 weeks (with 1-2 weeks buffer for unforeseen challenges)

---

## Next Steps

1. **Review and refine this plan**: Gather feedback from stakeholders, adjust priorities
2. **Set up development environment**: Clone pipeline repo, access Postgres, verify data
3. **Create new repository**: Initialize `football-analytics-app` with base structure
4. **Spike on key uncertainties**: 
   - Verify Postgres connection and schema
   - Test query performance with real data
   - Prototype one chart to validate visualization approach
5. **Begin Phase 1**: Set up project structure and DB connectivity
