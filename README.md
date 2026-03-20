# LoopCloser

[![Quality Gate](https://github.com/ScienceIsNeato/course_record_updater/workflows/Quality%20Gate/badge.svg)](https://github.com/ScienceIsNeato/course_record_updater/actions/workflows/quality-gate.yml)
[![Security Scan](https://github.com/ScienceIsNeato/course_record_updater/workflows/Security%20Scan/badge.svg)](https://github.com/ScienceIsNeato/course_record_updater/actions/workflows/security-scan.yml)
[![Pre-commit](https://github.com/ScienceIsNeato/course_record_updater/workflows/Pre-commit%20Hooks/badge.svg)](https://github.com/ScienceIsNeato/course_record_updater/actions/workflows/pre-commit.yml)

An enterprise-grade Flask web application for managing course assessment and outcome workflows with comprehensive quality gates and 80% test coverage.

## Features

- Manual entry of course details via a web form.
- Upload of `.docx` files for automatic data extraction (using format-specific adapters).
- Display of courses and related workflow data in a table.
- Inline editing and deletion of records.
- Persistence using SQLite (SQLAlchemy ORM).
- **Enterprise-grade quality gates** with 80% test coverage threshold
- **Automated security scanning** and dependency vulnerability checks
- **CI/CD integration** with GitHub Actions

## 🚀 Quality & CI/CD

This project maintains enterprise-grade quality standards:

- **80% Test Coverage Threshold**: Enforced locally and in CI
- **Automated Quality Gates**: Format, lint, security, type checking
- **Pre-commit Hooks**: Consistent code quality across contributors
- **Security Scanning**: Daily vulnerability checks with automatic issue creation
- **Multi-Python Support**: Tested on Python 3.9, 3.11, and 3.13

### Quick Start - Quality Checks

```bash
# Install development dependencies
pip install -r requirements-dev.txt

sm swab

# Run full PR validation
sm scour

# Security check (local scanners)
sm swab -g myopia:vulnerability-blindness.py --verbose
```

### Git Operations & Commit Messages

For commit messages, create a `COMMIT_MSG.txt` file with your message content to avoid quote escaping issues:

```bash
# Create commit message file
echo "fix: resolve failing tests" > COMMIT_MSG.txt

# Commit using the message file
git commit --file=COMMIT_MSG.txt
```

See [CI_SETUP_GUIDE.md](docs/setup/CI_SETUP_GUIDE.md) for comprehensive CI/CD documentation.

## 🎬 Demo & Workflow Walkthroughs

Product demonstration materials for key workflows:

- **[docs/workflow-walkthroughs/](docs/workflow-walkthroughs/)**: Workflow demonstration system
- **[single_term_outcome_management.md](docs/workflow-walkthroughs/single_term_outcome_management.md)**: Complete 30-minute workflow demo

### Interactive Demo

```bash
# Run interactive step-by-step demo
python docs/workflow-walkthroughs/scripts/run_demo.py single_term_outcome_management.md
```

### Manual Demo Setup

```bash
# Seed demo database
python scripts/seed_db.py --demo --clear --env dev

# Start server
bash scripts/restart_server.sh dev

# Access: http://localhost:3001
# Login: demo2025.admin@example.com / Demo2024!
```

## 🧪 Manual Testing & UAT

For comprehensive user acceptance testing of the authentication system:

- **[UAT_GUIDE.md](docs/testing/UAT_GUIDE.md)**: Complete manual testing protocol with role-based scenarios
- **[SMOKE_TESTING_GUIDE.md](docs/testing/SMOKE_TESTING_GUIDE.md)**: Quick smoke test procedures
- **[TESTING_STRATEGY.md](docs/testing/TESTING_STRATEGY.md)**: Overall testing approach and automation strategy

### Quick Testing Commands

```bash
# Quick frontend validation (5 seconds)
sm swab -g overconfidence:frontend-sanity --verbose

# Comprehensive smoke tests (30-60 seconds)
sm scour -g overconfidence:smoke --verbose

# Seed database with test data
python scripts/seed_db.py --clear
```

## Project Structure

```
.
├── src/                  # 🚀 Source code (Core application)
│   ├── app.py              # Main Flask application factory
│   ├── api/                # API route packages
│   ├── models/             # Data models
│   ├── services/           # Business logic services
│   ├── database/           # Database layer
│   └── utils/              # Shared utilities
├── config/               # ⚙️ Configuration files
├── data/                 # 💾 Database files and session data
├── build/                # 🏭 Build artifacts (coverage, reports)
├── demos/                # 🎬 Demo data and artifacts
├── docs/                 # 📚 Documentation
│   ├── architecture/       # System design
│   ├── setup/              # Environment, deployment, CI guides
│   ├── testing/            # Testing strategy, E2E, smoke, UAT
│   ├── quality/            # Quality gate and code quality guides
│   ├── requirements/       # User stories, specs, requirements
│   ├── demos/              # Demo scripts and walkthroughs
│   ├── process/            # Development workflows, antipatterns
│   └── decisions/          # Architecture decision records
├── archive/              # 📦 HISTORICAL/LEGACY DOCS
│   ├── planning/           # Old phase plans, timelines
│   ├── legacy/             # Migration docs, V1 designs
│   └── agent/              # AI agent context files
├── static/               # 🎨 Frontend assets (CSS, JS)
├── templates/            # 📄 HTML templates
├── tests/                # 🧪 Unit and integration tests
├── scripts/              # 🛠️ Utility and deployment scripts
└── README.md             # This file
```

### 📁 Documentation Organization

| Category         | Location             | Contents                              |
| ---------------- | -------------------- | ------------------------------------- |
| **Architecture** | `docs/architecture/` | System design, data models, site maps |
| **Setup**        | `docs/setup/`        | Environment, deployment, CI/CD guides |
| **Testing**      | `docs/testing/`      | Test strategy, E2E, smoke testing     |
| **Requirements** | `docs/requirements/` | User stories, specifications          |
| **Demos**        | `docs/demos/`        | Demo scripts, walkthroughs            |
| **Legacy**       | `archive/`           | Old plans, migrations, PR notes       |

## Setup and Running

1.  **Prerequisites:**
    - Python 3 (tested with 3.13, adjust as needed)

- No external cloud prerequisites required for persistence (SQLite database created automatically).

2.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

3.  **Create and activate a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows use `venv\Scripts\activate`
    ```

4.  **Install dependencies:**

    ```bash
    python -m pip install -r requirements.txt
    ```

5.  **Set Google Application Credentials:**
    Make sure the `GOOGLE_APPLICATION_CREDENTIALS` environment variable points to your service account key file, or that you are logged in via `gcloud auth application-default login`.
    ```bash
    # Example for service account key:
    export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/loopcloser-service-account.json"
    ```
6.  **Run the application:**
    ```bash
    python src/app.py
    ```
    The application should be accessible at `http://localhost:8080` (or the port specified by the `PORT` environment variable).

## Running Tests

1.  Ensure the virtual environment is activated and dependencies are installed.
2.  **Unit Tests:** Run tests that mock external services:
    ```bash
    python -m pytest
    ```
3.  **Integration Tests:** No external emulator required.

    ```bash
    python -m pytest tests/integration -m integration
    ```

## Development Notes

- This project uses Flask, SQLite (via SQLAlchemy), and python-docx.
- Follow TDD principles where possible.
- Run tests after any code changes.
- See `PROJECT_OVERVIEW.md` for architecture details.
- See `STATUS.md` for current development progress.

## Test Passwords and Secrets Policy

- **Do not hardcode password literals in tests.** Use centralized test passwords from `src/utils/constants.py`:
  - `GENERIC_PASSWORD` - Use everywhere except password validation testing
  - `WEAK_PASSWORD` - For testing rejection of weak passwords
  - `INVALID_PASSWORD` - For testing password complexity requirements
- When adding a new test secret constant intentionally, regenerate and commit the detect-secrets baseline (`.secrets.baseline`) so the scanner records the intentional test secret.
- Contributors should import the constant from `src.utils.constants` in tests instead of using inline literals.
