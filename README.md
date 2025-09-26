# Course Record Updater

[![Quality Gate](https://github.com/ScienceIsNeato/course_record_updater/workflows/Quality%20Gate/badge.svg)](https://github.com/ScienceIsNeato/course_record_updater/actions/workflows/quality-gate.yml)
[![Security Scan](https://github.com/ScienceIsNeato/course_record_updater/workflows/Security%20Scan/badge.svg)](https://github.com/ScienceIsNeato/course_record_updater/actions/workflows/security-scan.yml)
[![Pre-commit](https://github.com/ScienceIsNeato/course_record_updater/workflows/Pre-commit%20Hooks/badge.svg)](https://github.com/ScienceIsNeato/course_record_updater/actions/workflows/pre-commit.yml)

A enterprise-grade Flask web application for managing course records with comprehensive quality gates and 80% test coverage.

## Features

*   Manual entry of course details via a web form.
*   Upload of `.docx` files for automatic data extraction (using format-specific adapters).
*   Display of course records in a table.
*   Inline editing and deletion of records.
*   Persistence using Google Cloud Firestore.
*   **Enterprise-grade quality gates** with 80% test coverage threshold
*   **Automated security scanning** and dependency vulnerability checks
*   **CI/CD integration** with GitHub Actions

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

# Run fast commit validation (excludes slow security & sonar checks)
python scripts/ship_it.py

# Run full PR validation (all checks including security & sonar)
python scripts/ship_it.py --validation-type PR

# Install pre-commit hooks
pre-commit install
```

### Git Operations & Commit Messages
For commit messages, create a `COMMIT_MSG.txt` file with your message content to avoid quote escaping issues:
```bash
# Create commit message file
echo "fix: resolve failing tests" > COMMIT_MSG.txt

# Commit using the message file
git commit --file=COMMIT_MSG.txt
```

See [CI_SETUP_GUIDE.md](CI_SETUP_GUIDE.md) for comprehensive CI/CD documentation.

## 🧪 Manual Testing & UAT

For comprehensive user acceptance testing of the authentication system:
- **[UAT_GUIDE.md](UAT_GUIDE.md)**: Complete manual testing protocol with role-based scenarios
- **[SMOKE_TESTING_GUIDE.md](SMOKE_TESTING_GUIDE.md)**: Quick smoke test procedures
- **[TESTING_STRATEGY.md](TESTING_STRATEGY.md)**: Overall testing approach and automation strategy

### Quick Testing Commands
```bash
# Quick frontend validation (5 seconds)
./check_frontend.sh

# Comprehensive smoke tests (30-60 seconds)  
./run_smoke_tests.sh

# Seed database with test data
python scripts/seed_db.py --clear
```

## Project Structure

```
.
├── adapters/             # Modules for parsing different input formats
│   ├── __init__.py
│   ├── base_adapter.py     # Base validation/parsing logic
│   ├── dummy_adapter.py    # Example file adapter
│   └── file_adapter_dispatcher.py # Handles loading specific file adapters
├── planning/             # 📋 PROJECT PLANNING & DOCUMENTATION
│   ├── documentation/      # Technical specifications and requirements
│   │   ├── AUTH_REQUIREMENTS.md    # Authentication and authorization design
│   │   ├── DATA_MODEL.md           # Database entities and relationships
│   │   ├── DATA_ENTRY_STRATEGY.md  # Data input and validation approach
│   │   ├── EXECUTION_PLAN.md       # Development milestones and timeline
│   │   ├── PERMISSION_MATRIX.md    # User role permissions checklist
│   │   ├── PRICING_STRATEGY.md     # Business model and pricing tiers
│   │   └── STAKEHOLDER_QUESTIONS.md # Questions for client meetings
│   ├── user_stories/       # User workflows by role
│   │   ├── site_admin/           # Global admin user stories
│   │   ├── institution_administrator/ # Institution-level user stories
│   │   ├── program_administrator/     # Program-level user stories
│   │   └── regular_user/             # Faculty/instructor user stories
│   └── meetings/           # Meeting notes and decisions
├── research/             # 🔍 STAKEHOLDER RESEARCH & ANALYSIS
│   └── CEI/                # College of Eastern Idaho pilot research
│       ├── README.md                 # CEI contact info and materials
│       ├── VIDEO_ANALYSIS.md         # Analysis of stakeholder video
│       ├── SPREADSHEET_ANALYSIS.md   # Analysis of current data structure
│       ├── BRIDGE_STRATEGY.md        # Migration approach and Access export
│       └── SESSION_SUMMARY.md        # Key insights and discoveries
├── static/               # Static files (CSS, JavaScript)
│   └── script.js
├── templates/            # Flask HTML templates
│   └── index.html
├── tests/                # Unit and integration tests
│   ├── __init__.py
│   ├── test_base_adapter.py
│   ├── test_database_service.py
│   ├── test_dummy_adapter.py
│   └── test_file_adapter_dispatcher.py
├── .gitignore            # Git ignore file
├── app.py                # Main Flask application
├── database_service.py   # Handles Firestore interactions
├── PROJECT_OVERVIEW.md   # High-level project goals and architecture
├── README.md             # This file
├── requirements.txt      # Python dependencies
├── STATUS.md             # Current development status and milestones
└── venv/                 # Python virtual environment (if created)
```

### 📁 Documentation Organization Rules

**IMPORTANT:** All project documentation follows this structure:

- **`planning/documentation/`** - Technical specifications, requirements, and design documents
- **`research/`** - Stakeholder analysis, data analysis, and external research materials
- **Root level** - Only core project files (README, STATUS, PROJECT_OVERVIEW)
- **NO `docs/` folder** - This was removed to prevent confusion

When adding new documentation:
- Technical specs → `planning/documentation/`
- User workflows → `planning/user_stories/[user_role]/`
- Stakeholder research → `research/[client_name]/`
- Meeting notes → `planning/meetings/`

## Setup and Running

1.  **Prerequisites:**
    *   Python 3 (tested with 3.13, adjust as needed)
    *   Google Cloud SDK (`gcloud`) installed and configured (for Firestore access)
    *   Credentials for Google Cloud Firestore (set up via `GOOGLE_APPLICATION_CREDENTIALS` environment variable or service account/default login).

2.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd course_record_updater
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
    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"
    ```

6.  **Run the application:**
    ```bash
    python app.py
    ```
    The application should be accessible at `http://localhost:8080` (or the port specified by the `PORT` environment variable).

## Running Tests

1.  Ensure the virtual environment is activated and dependencies are installed.
2.  **Unit Tests:** Run tests that mock external services:
    ```bash
    python -m pytest
    ```
3.  **Integration Tests (Requires Firestore Emulator):**

    **--> IMPORTANT: The Firestore emulator MUST be running in a separate terminal before executing these tests. <--**

    *   **Install Emulator:** If you haven't already, install the emulator component:
        ```bash
        gcloud components install cloud-firestore-emulator
        ```
    *   **Run Emulator:** In a **separate terminal window**, navigate to your project directory (optional but good practice) and start the emulator. Note the host and port it outputs (usually `localhost:8086` or similar).
        ```bash
        # In Terminal 1 (Leave this running):
        gcloud beta emulators firestore start --host-port=localhost:8086
        ```
    *   **Set Environment Variable & Run Tests:** In the **original terminal** (where your venv is active), set the `FIRESTORE_EMULATOR_HOST` variable and run pytest. The tests should automatically connect to the running emulator.
        ```bash
        # In Terminal 2 (Your testing terminal):
        export FIRESTORE_EMULATOR_HOST="localhost:8086"
        python -m pytest
        # Or, combining the export and run:
        # FIRESTORE_EMULATOR_HOST="localhost:8086" python -m pytest

        # Optionally run only integration tests if tagged:
        # FIRESTORE_EMULATOR_HOST="localhost:8086" python -m pytest -m integration
        ```
    *   **Stopping the Emulator:** When finished, go back to Terminal 1 and press `Ctrl+C` to stop the emulator process.

## Development Notes

*   This project uses Flask, Firestore, and python-docx.
*   Follow TDD principles where possible.
*   Run tests after any code changes.
*   See `PROJECT_OVERVIEW.md` for architecture details.
*   See `STATUS.md` for current development progress.
