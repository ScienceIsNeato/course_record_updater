# Repository Guidelines

> 📌 **Need the latest priorities or risk notes?** See `AGENT_LESSONS_LEARNED.md` for the current lessons log before you start coding.

## Project Structure & Module Organization
Core Flask logic lives in `app.py`, with domain services split across `*_service.py` modules for auth, registration, invitations, and data access. File parsing adapters sit in `adapters/` and share a common base class for extension. Web assets are separated into `templates/` for Jinja views and `static/` for JavaScript and CSS. Automation lives in `scripts/`, notably `ship_it.py` for composite quality gates. Tests are organised under `tests/unit` and `tests/integration`; keep shared fixtures and marks in `tests/conftest.py`. Planning artefacts stay in `planning/` and stakeholder research in `research/` to keep delivery code uncluttered.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: Create and activate the virtual environment.
- `pip install -r requirements-dev.txt`: Install runtime and contributor tooling.
- `./restart_server.sh`: Run the Flask server locally (defaults to port 3001).
- `python scripts/ship_it.py`: Fast validation covering lint, typing, and unit tests.
- `python scripts/ship_it.py --validation-type PR`: Full gate including security and sonar checks.
- `pytest --cov=. --cov-report=term-missing --cov-fail-under=80`: Run the suite with the enforced coverage bar.

## Coding Style & Naming Conventions
Format Python with `black` (line length 88) and organise imports with `isort`. Lint changes with `flake8` and `pylint`; maintain type hints so `mypy` passes. Use 4-space indentation, `snake_case` for modules and functions, `PascalCase` for classes, and reserve `UPPER_SNAKE_CASE` for constants. Templates follow Jinja conventions; keep ES6-ready helpers in `static/` with filenames that mirror their template consumers.

## Testing Guidelines
Add unit specs under `tests/unit/test_<feature>.py` and integration suites under `tests/integration/`. Use the existing markers (`unit`, `integration`, `slow`) to scope runs. Integration tests expect the Firestore emulator: `gcloud beta emulators firestore start --host-port localhost:8080`. Maintain ≥80% coverage; include regression fixtures when touching adapters or Firestore access paths.

## Commit & Pull Request Guidelines
Follow the Conventional Commit prefix (`feat:`, `fix:`, `refactor:`) used in the history (see `COMMIT_MSG.txt`). Keep subjects imperative and ≤72 characters, and squash noisy fixups before opening a PR. Each PR should include a crisp summary, linked issue, verification notes (commands run), and screenshots for UI-facing updates. Update docs, fixtures, or scripts alongside code changes to avoid blocking automation.

## Environment & Configuration Tips
Set `GOOGLE_APPLICATION_CREDENTIALS` to a valid Firestore service account or log in through `gcloud auth application-default login`. Use local `.env` files or shell exports—never commit secrets. Adjust `PORT` and session settings via environment variables when running multiple instances so concurrent agents stay isolated.
