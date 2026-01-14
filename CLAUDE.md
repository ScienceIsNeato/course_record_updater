# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Loopcloser (internally: LoopCloser) is an enterprise-grade Flask web application for managing course learning outcomes and assessment data. It serves educational institutions with multi-tenancy, role-based authentication, and comprehensive quality gates maintaining 80% test coverage.

**Key Technologies:**
- Backend: Python 3.13 (Flask 3.1+), SQLAlchemy 2.0+
- Frontend: Vanilla JavaScript, HTML templates with Jinja2
- Database: SQLite (via SQLAlchemy ORM)
- Testing: pytest with parallel execution (pytest-xdist), Playwright for E2E
- Quality: Black, isort, flake8, pylint, mypy, bandit, safety

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install frontend dependencies
npm install
```

### Running the Application
```bash
# Start development server (port 3001)
bash scripts/restart_server.sh dev

# Start E2E test server (port 3002)
bash scripts/restart_server.sh e2e

# Direct Flask run (port 8080)
python src/app.py
```

**Important:** Use `restart_server.sh` for consistent environment setup. The script handles database path configuration, session directories, and environment-specific settings.

### Quality Gates & Testing

**Primary Quality Gate (Always Use This):**
```bash
# Fast commit validation (excludes slow checks like smoke tests)
python scripts/ship_it.py

# Full PR validation (all checks + comment resolution)
python scripts/ship_it.py --checks PR

# Run specific check suites
python scripts/ship_it.py --checks format lint tests
python scripts/ship_it.py --checks security-local  # Security without safety (no network)
python scripts/ship_it.py --checks frontend-check  # Quick JS validation (5s)
python scripts/ship_it.py --checks smoke          # Critical path tests (30-60s)
```

**IMPORTANT:** Always use `ship_it.py` for running tests. Do NOT run `pytest` or `npm test` directly unless running a single test file for quick verification during development.

**Single Test File Verification (Development Only):**
```bash
# Quick verification of a single test file during development
pytest tests/unit/test_auth_service.py
pytest tests/integration/test_offering_workflow.py -v

# Run specific test by name
pytest tests/unit/test_auth_service.py::test_login_success -v
```

**Frontend Testing:**
```bash
# Run through ship_it.py (preferred)
python scripts/ship_it.py --checks frontend-check

# Direct npm commands (if needed for development)
npm test
npm run test:coverage
npm run lint
npm run format:check
```

### Code Quality & Formatting
```bash
# Auto-fix Python formatting (safe to run anytime)
black .
isort .

# Lint Python
flake8 src tests
pylint src tests

# Type checking
mypy src

# Security scanning (local, no network)
bandit -r src -f json -o bandit-report.json
semgrep --config auto src

# JavaScript quality
npm run lint:fix
npm run format
```

### Database Operations
```bash
# Seed database with demo data
python scripts/seed_db.py --demo --clear --env dev

# Seed with test data
python scripts/seed_db.py --clear

# Create specific accounts
python scripts/seed_worker_accounts.py

# Direct import from CLI
python src/import_cli.py --file data/example.csv
```

## Architecture

### Application Structure

```
src/
├── app.py              # Flask app factory, main routes, CSRF protection
├── api_routes.py       # Legacy monolithic API (being extracted to api/)
├── api/                # New modular API structure (in progress)
│   ├── routes/         # Domain-specific blueprints
│   │   ├── audit.py
│   │   ├── bulk_email.py
│   │   ├── clo_workflow.py
│   │   ├── dashboard.py
│   │   └── management.py
│   └── utils.py        # API helpers
├── services/           # Business logic layer
│   ├── auth_service.py           # Authentication & authorization
│   ├── dashboard_service.py      # Dashboard data aggregation
│   ├── bulk_email_service.py     # Bulk email jobs
│   ├── import_service.py         # Data import/CSV parsing
│   ├── export_service.py         # Data export to Excel
│   └── institution_service.py    # Multi-tenancy logic
├── database/           # Database abstraction layer
│   ├── database_service.py       # Main facade, backwards compatibility
│   ├── database_factory.py       # Service initialization
│   ├── database_interface.py     # Abstract interface
│   ├── database_sqlite.py        # SQLite implementation
│   └── database_validator.py     # Schema validation
├── models/             # SQLAlchemy models
│   ├── models_sql.py   # All SQLAlchemy table definitions
│   └── models.py       # Legacy/compatibility
├── adapters/           # Data parsing/validation (CSV, DOCX)
├── email_providers/    # Email backend abstraction (Ethereal, Gmail SMTP)
├── bulk_email_models/  # Bulk email job domain models
└── utils/              # Shared utilities
    ├── constants.py    # Application constants
    ├── logging_config.py  # Centralized logging
    ├── term_utils.py   # Academic term calculations
    └── time_utils.py   # Timezone-aware datetime utilities
```

### Key Architectural Patterns

**1. Service Layer Pattern**
Business logic lives in `src/services/`. Services are stateless, dependency-injected, and thoroughly tested.

**2. Database Abstraction**
- `database_service.py` provides a backwards-compatible facade
- All database operations go through `database_factory.py` → `database_sqlite.py`
- Direct SQLAlchemy session access via `db.sqlite.session`
- Models defined in `models_sql.py` using declarative base

**3. API Evolution**
- **Legacy:** `api_routes.py` contains monolithic API (5000+ lines)
- **New:** `src/api/routes/` contains extracted domain blueprints
- **Migration:** Gradually extracting routes from api_routes.py to modular blueprints

**4. Multi-Tenancy**
- Institution-scoped data isolation
- All queries automatically filtered by `institution_id`
- Current user's institution retrieved via `get_current_user()` from session

**5. Authentication & Authorization**
- Session-based auth (Flask-Session with filesystem storage)
- CSRF protection enabled globally (CSRFProtect)
- Decorators: `@login_required`, `@permission_required`
- Roles: Site Admin, Institution Admin, Program Admin, Instructor

### Database Schema

**Core Entities:**
- **Institutions** → **Users** (instructors, admins)
- **Terms** (academic periods)
- **Programs** (e.g., "Computer Science BS")
- **Courses** (e.g., "CS 101") ↔ **Programs** (many-to-many)
- **Course Offerings** (course in a specific term)
- **Course Sections** (specific class section of an offering)
- **Course Outcomes** (learning objectives for a course)

**Key Relationships:**
- Institution has many Users, Programs, Terms, Courses
- Course has many Offerings (one per term)
- Offering has many Sections (multiple instructors/times)
- Course has many Outcomes (learning objectives)

### Testing Strategy

**Test Organization:**
```
tests/
├── unit/           # Fast, isolated unit tests (services, utils)
├── integration/    # Database integration tests (SQLite)
├── smoke/          # Critical path sanity checks (login, dashboard)
├── e2e/            # End-to-end browser tests (Playwright)
├── third_party/    # External service tests (email providers)
├── javascript/     # Frontend JavaScript tests (Jest)
└── fixtures/       # Shared test fixtures
```

**Test Markers (pytest):**
- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Database integration tests
- `@pytest.mark.smoke` - Critical path tests
- `@pytest.mark.e2e` - Browser automation tests (excluded from coverage)
- `@pytest.mark.slow` - Long-running tests (deselect with `-m "not slow"`)

**Key Testing Conventions:**
1. **CSRF Always Enabled in Tests:** All test clients have CSRF wrapper (see `conftest.py`)
2. **Database Fixtures:** Use `db_session`, `init_schema`, `test_db` fixtures
3. **Auth Fixtures:** Use `authenticated_client` fixture for logged-in tests
4. **Parallel Execution:** Tests must be thread-safe (use unique IDs, isolated data)

### CSRF Protection

CSRF is **always enabled** in production and tests. Key patterns:

```python
# In tests, client auto-injects CSRF token (conftest.py wrapper)
response = client.post('/api/endpoint', json=data)

# Manual CSRF token access (if needed)
csrf_token = _get_csrf_token_from_session_or_generate(client)
response = client.post('/api/endpoint',
    headers={'X-CSRFToken': csrf_token},
    json=data)

# In templates, use {{ csrf_token() }}
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
</form>
```

### Code Quality Requirements

**Coverage Threshold:** 80% (enforced in CI and locally)

**Pre-commit Hooks:**
- detect-secrets (secret scanning)
- black (auto-format Python)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking)

**CI Quality Gates:**
1. Python formatting & linting (black, isort, flake8, pylint)
2. JavaScript formatting & linting (ESLint, Prettier)
3. Type checking (mypy --strict)
4. Tests with 80% coverage
5. Security scanning (bandit, semgrep, safety)
6. Import validation
7. Comment resolution check (PRs only)

### Common Patterns & Best Practices

**1. Getting Current User & Institution:**
```python
from src.services.auth_service import get_current_user

user = get_current_user()
institution_id = user['institution_id']
user_id = user['id']
```

**2. Database Operations:**
```python
from src.database.database_service import db

# Query with auto-commit
courses = db.get_courses_by_institution(institution_id)

# Manual transaction
with db.sqlite.session.begin():
    course = Course(name="New Course", institution_id=institution_id)
    db.sqlite.session.add(course)
```

**3. Error Handling in APIs:**
```python
@api.route('/endpoint', methods=['POST'])
def endpoint():
    try:
        # Business logic
        return jsonify({'success': True, 'data': result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
```

**4. Time & Date Handling:**
```python
from src.utils.time_utils import get_current_time
from src.utils.term_utils import get_current_term, TermGenerator

# Always use timezone-aware datetime
now = get_current_time()  # Returns datetime with UTC or institution timezone

# Academic term calculations
current_term = get_current_term(institution_id)
term_gen = TermGenerator(start_year=2025)
```

**5. Logging:**
```python
from src.utils.logging_config import get_app_logger

logger = get_app_logger()
logger.info("Operation completed")
logger.error("Error occurred", exc_info=True)
```

### Development Workflow

**Feature Development:**
1. Create feature branch from `main`
2. Run `python scripts/ship_it.py` frequently during development
3. Ensure all tests pass: `python scripts/ship_it.py --checks tests`
4. Before commit: `python scripts/ship_it.py` (fast validation)
5. Before PR: `python scripts/ship_it.py --validation-type PR` (full validation)

**Commit Messages:**
Use conventional commits format:
```
feat: add bulk email job status tracking
fix: resolve CSRF token validation in API routes
refactor: extract dashboard routes to separate blueprint
test: add integration tests for course offering workflow
docs: update API documentation for term endpoints
```

**Git Operations:**
```bash
# Create commit message file to avoid quote escaping issues
echo "fix: resolve failing tests" > COMMIT_MSG.txt
git commit --file=COMMIT_MSG.txt
```

## Important Notes

**Database Paths:**
- Development: `course_records_dev.db`
- E2E Tests: `course_records_e2e.db`
- Unit Tests: `course_records_test.db`
- Production: Configured via `DB_PATH` environment variable

**Port Configuration:**
- Dev server: 3001
- E2E server: 3002
- Direct Flask: 8080

**Environment Variables:**
See `.envrc.template` for all configuration options. Key variables:
- `APP_ENV` (dev|e2e|production)
- `DB_PATH` (database file path)
- `SECRET_KEY` (Flask session secret)
- `FLASK_DEBUG` (true|false)
- `EMAIL_WHITELIST` (comma-separated, for testing)
- `WTF_CSRF_ENABLED` (true|false, default: true)

**Security Notes:**
- Never commit `.envrc` (contains secrets)
- Use `.envrc.template` as reference
- All passwords hashed with bcrypt
- CSRF protection enabled globally
- Session data stored in filesystem (`flask_session/`)

## Demo & UAT Resources

**Manual Testing Guides:**
- `docs/testing/UAT_GUIDE.md` - Complete user acceptance testing protocol
- `docs/testing/SMOKE_TESTING_GUIDE.md` - Quick smoke test procedures

**Workflow Demos:**
- `docs/workflow-walkthroughs/single_term_outcome_management.md` - 30-minute demo
- Run interactive demo: `python docs/workflow-walkthroughs/scripts/run_demo.py single_term_outcome_management.md`

**Demo Setup:**
```bash
python scripts/seed_db.py --demo --clear --env dev
bash scripts/restart_server.sh dev
# Access: http://localhost:3001
# Login: demo2025.admin@example.com / Demo2024!
```

## Troubleshooting

**Tests failing with CSRF errors:**
- Ensure using `client` fixture from conftest.py (has CSRF wrapper)
- Check `WTF_CSRF_ENABLED` environment variable

**Database locked errors:**
- Stop any running servers: `pkill -f "python.*app.py"`
- Remove lock: `rm course_records_*.db-*`

**Import errors:**
- Ensure `src` is in PYTHONPATH: `export PYTHONPATH=src:.`
- Check virtual environment activated: `which python` should show venv path

**Quality gate failures:**
- Run individual checks: `python scripts/ship_it.py --checks format`
- Auto-fix formatting: `black . && isort .`
- Check detailed output: `python scripts/ship_it.py --verbose`

**Coverage below 80%:**
- Run with coverage report via ship_it: `python scripts/ship_it.py --checks tests`
- For detailed HTML report, the quality gate generates `htmlcov/index.html`
- Add tests for uncovered code paths
