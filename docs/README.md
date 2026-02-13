
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.6-336791.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.51-23BF00.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.3+-BC00BF.svg)
![Plotly](https://img.shields.io/badge/Plotly-6.5+-0089BF.svg)

# ⚽ Football Analytics Dashboard

A Streamlit-based web application for visualizing football analytics, team performance metrics, match predictions, and league insights. This app connects to a PostgreSQL database populated by a separate data pipeline to provide real-time football statistics and predictions.

## 🎯 Features

- **Multi-League Support**: Analyze teams across different leagues (Ekstraklasa and more)
- **Upcoming Fixtures**: View upcoming matches with predictions and team form
- **Team Statistics**: Deep dive into attack, defense, possession, and discipline metrics
- **Head-to-Head Analysis**: Compare historical matchups between teams
- **Performance Insights**: League-wide trends, anomalies, and performance tracking
- **Interactive Visualizations**: Charts and graphs powered by Plotly and Altair
- **Data Freshness Monitoring**: Track when data was last updated
- **Export Capabilities**: Download data as CSV and charts as PNG/SVG

## 📋 Prerequisites

- **Python 3.11+**
- **PostgreSQL 17+** (with populated gold schema from data pipeline)
- **Docker & Docker Compose** (optional, for containerized deployment)
- **Git**

## 🚀 Quick Start

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
streamlit run app/app.py
```

The app will open automatically in your browser at `http://localhost:8501`

## 🐳 Docker Deployment

### Build and Run with Docker Compose

```bash
# Build the image
docker-compose build

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop the application
docker-compose down
```

The application will be available at `http://localhost:8501`

### Environment Variables in Docker

When using Docker, ensure your `.env` file is configured with:

```env
POSTGRES_HOST=host.docker.internal  # For connecting to host machine's Postgres
# OR
POSTGRES_HOST=postgres  # If using a Postgres service in docker-compose
```

## 📁 Project Structure

```
Football-dashboard-app/
├── app/
│   └── app.py                    # Main Streamlit application entry point
├── components/                   # Reusable UI components (planned)
├── config/
│   └── settings.py              # Pydantic settings and configuration
├── services/
│   ├── __init__.py
│   └── db.py                    # Database connection and session management
├── tests/
│   └── test_db_connection.py    # Database connectivity tests
├── docs/
│   └── plan.md                  # Detailed implementation plan
├── .env.example                 # Environment variables template
├── .gitignore
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Container image definition
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🔧 Configuration

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

These tables should be populated by your data pipeline (see [docs/plan.md](docs/plan.md) for details).

## 🧪 Testing

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

## 🔍 Troubleshooting

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

### Docker Issues

**Problem:** Cannot connect to database from Docker container

**Solution:** Use `host.docker.internal` as `POSTGRES_HOST` when connecting to database on host machine

**Problem:** Port 8501 already in use

**Solution:** Either stop the conflicting service or change the port mapping in [docker-compose.yml](docker-compose.yml):
```yaml
ports:
  - "8502:8501"  # Use port 8502 on host
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'services'`

**Solution:** Ensure you're running from the project root and Python path is configured correctly. The [app/app.py](app/app.py) includes path configuration, but verify:

```python
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(PROJECT_ROOT)
```

## 📊 Current Implementation Status

### ✅ Completed (Phase 1: Foundation)
- [x] Project structure and repository initialization
- [x] Database connection with SQLAlchemy ([services/db.py](services/db.py))
- [x] Configuration management with Pydantic ([config/settings.py](config/settings.py))
- [x] Basic Streamlit app scaffold ([app/app.py](app/app.py))
- [x] Docker containerization
- [x] Environment variable validation
- [x] Database health check functionality
- [x] Initial test suite

### 🚧 In Progress / Planned
- [ ] SQLAlchemy models for gold marts (Phase 2)
- [ ] Parameterized query functions (Phase 2)
- [ ] UI pages: Fixtures, Teams, Head-to-Head, Insights (Phase 3)
- [ ] Interactive visualizations with Plotly/Altair (Phase 4)
- [ ] Caching strategies (Phase 2)
- [ ] Multi-league support (Phase 6)
- [ ] Match predictions display (Phase 5)

See [docs/plan.md](docs/plan.md) for the complete implementation roadmap.

## 🛠️ Development

### Code Quality

We use `pytest` for testing. Before committing, ensure:

```bash
# Run tests
pytest

# Check for import errors
python -c "from services.db import check_connection; print('✓ Imports OK')"
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement feature following project structure
3. Add tests in `tests/`
4. Update documentation
5. Submit pull request

## 📖 Documentation

- **Implementation Plan**: [docs/plan.md](docs/plan.md) - Detailed 7-week roadmap
- **License**: [LICENSE](LICENSE) - MIT License

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Database layer powered by [SQLAlchemy](https://www.sqlalchemy.org/)
- Visualizations using [Plotly](https://plotly.com/) and [Altair](https://altair-viz.github.io/)
- Configuration management with [Pydantic](https://docs.pydantic.dev/)

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Review troubleshooting section above
- Check [docs/plan.md](docs/plan.md) for architectural details

---

**Status**: Phase 1 Complete ✅ | Active Development 🚀

Built with ⚽ for football analytics