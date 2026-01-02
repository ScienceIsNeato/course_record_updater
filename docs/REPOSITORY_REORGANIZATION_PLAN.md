# Repository Reorganization Plan

**Goal**: Clean up root directory chaos by moving source code to `src/` and organizing supporting files into logical directories.

---

## 🎯 Proposed Directory Structure

```
course_record_updater/
├── src/                          # All Python application code
│   ├── api/                      # API blueprint modules (MOVED from root/api/)
│   ├── adapters/                 # Import adapters (MOVED from root/adapters/)
│   ├── email_providers/          # Email provider implementations (MOVED from root)
│   ├── bulk_email_models/        # Bulk email models (MOVED from root)
│   ├── services/                 # NEW: Service layer modules
│   │   ├── __init__.py
│   │   ├── auth_service.py       # MOVED from root
│   │   ├── audit_service.py      # MOVED from root
│   │   ├── dashboard_service.py  # MOVED from root
│   │   ├── email_service.py      # MOVED from root
│   │   ├── import_service.py     # MOVED from root
│   │   ├── invitation_service.py # MOVED from root
│   │   ├── login_service.py      # MOVED from root
│   │   ├── password_service.py   # MOVED from root
│   │   ├── password_reset_service.py  # MOVED from root
│   │   ├── registration_service.py    # MOVED from root
│   │   ├── export_service.py     # MOVED from root
│   │   ├── bulk_email_service.py # MOVED from root
│   │   └── clo_workflow_service.py    # MOVED from root
│   ├── database/                 # NEW: Database layer
│   │   ├── __init__.py
│   │   ├── database_factory.py   # MOVED from root
│   │   ├── database_interface.py # MOVED from root
│   │   ├── database_service.py   # MOVED from root
│   │   ├── database_sql.py       # MOVED from root
│   │   ├── database_sqlite.py    # MOVED from root
│   │   └── database_validator.py # MOVED from root
│   ├── models/                   # NEW: Data models
│   │   ├── __init__.py
│   │   ├── models.py             # MOVED from root (Pydantic models)
│   │   └── models_sql.py         # MOVED from root (SQLAlchemy models)
│   ├── utils/                    # NEW: Utility modules
│   │   ├── __init__.py
│   │   ├── constants.py          # MOVED from root
│   │   ├── logging_config.py     # MOVED from root
│   │   └── term_utils.py         # MOVED from root
│   ├── cli/                      # NEW: CLI tools
│   │   ├── __init__.py
│   │   └── import_cli.py         # MOVED from root
│   ├── __init__.py
│   ├── app.py                    # MOVED from root (Flask app)
│   └── api_routes.py             # MOVED from root (main API routes)
│
├── static/                       # Frontend assets (STAYS at root - Flask convention)
├── templates/                    # HTML templates (STAYS at root - Flask convention)
├── tests/                        # Test suite (STAYS at root - Python convention)
├── scripts/                      # Utility scripts (STAYS at root)
├── docs/                         # Documentation (STAYS at root)
│
├── config/                       # NEW: Configuration files
│   ├── .coveragerc               # MOVED from root
│   ├── .eslintrc.js              # MOVED from root
│   ├── .eslintignore             # MOVED from root
│   ├── .prettierrc               # MOVED from root
│   ├── .pre-commit-config.yaml   # MOVED from root
│   ├── pytest.ini                # MOVED from root
│   ├── jest.config.js            # MOVED from root
│   ├── sonar-project.properties  # MOVED from root
│   └── .safety-project.ini       # MOVED from root
│
├── build/                        # NEW: Build artifacts & reports
│   ├── coverage/                 # MOVED from root
│   ├── htmlcov/                  # MOVED from root
│   ├── .scannerwork/             # MOVED from root
│   ├── .sonar_run_metadata.json  # MOVED from root
│   ├── coverage.xml              # MOVED from root
│   ├── diff-coverage-report.html # MOVED from root
│   ├── test-results.xml          # MOVED from root
│   ├── bandit-report.json        # MOVED from root
│   ├── semgrep-report.json       # MOVED from root
│   └── safety-report.txt         # MOVED from root
│
├── data/                         # NEW: Runtime data files
│   ├── databases/                # NEW: Database files
│   │   ├── course_records.db     # MOVED from root
│   │   ├── course_records_dev.db # MOVED from root
│   │   └── course_records_e2e.db # MOVED from root
│   ├── session/                  # MOVED from root
│   └── flask_session/            # MOVED from root
│
├── logs/                         # Application logs (STAYS at root - already organized)
│
├── archive/                      # OLD: Archive directory (cleanup candidate)
├── archives/                     # OLD: Archives directory (cleanup candidate)
├── ARCHIVED/                     # OLD: Archived directory (cleanup candidate)
├── research/                     # Research & exploration (KEEP for now)
├── demo_data/                    # Demo/test data files (KEEP)
├── demo_artifacts/               # Demo outputs (KEEP)
├── demos/                        # Demo scripts (KEEP)
│
├── .github/                      # GitHub workflows (STAYS)
├── .vscode/                      # VSCode settings (STAYS)
├── .agent/                       # Agent configuration (STAYS)
├── cursor-rules/                 # Cursor rules (STAYS)
│
├── .git/                         # Git repository (STAYS)
├── .gitignore                    # Git ignore (STAYS)
├── .gitattributes                # Git attributes (STAYS)
├── .gcloudignore                 # Cloud ignore (STAYS)
├── .envrc                        # Direnv config (STAYS)
├── .envrc.template               # Direnv template (STAYS)
│
├── node_modules/                 # NPM dependencies (git-ignored, STAYS)
├── venv/                         # Python virtual env (git-ignored, STAYS)
├── __pycache__/                  # Python cache (git-ignored, STAYS)
├── .mypy_cache/                  # Mypy cache (git-ignored, STAYS)
├── .pytest_cache/                # Pytest cache (git-ignored, STAYS)
├── .sonarlint/                   # SonarLint cache (git-ignored, STAYS)
│
├── temp_logs/                    # Temporary logs (CLEANUP)
├── temp_e2e_failed/              # Temporary E2E artifacts (CLEANUP)
├── build-output/                 # Build output (CLEANUP/MOVE to build/)
│
├── Dockerfile                    # Docker configuration (STAYS)
├── requirements.txt              # Python dependencies (STAYS)
├── requirements-dev.txt          # Dev dependencies (STAYS)
├── package.json                  # NPM configuration (STAYS)
├── package-lock.json             # NPM lock file (STAYS)
├── conftest.py                   # Pytest root config (STAYS - needed at root for pytest)
│
├── README.md                     # Project README (STAYS)
├── AGENTS.md                     # Agent documentation (STAYS)
├── STATUS.md                     # Current status (STAYS)
├── VERSION                       # Version file (STAYS)
├── COMMIT_MSG.txt                # Temp commit message (CLEANUP)
│
├── check_frontend.sh             # Utility script (MOVE to scripts/)
├── restart_server.sh             # Utility script (MOVE to scripts/)
├── run_uat.sh                    # Utility script (MOVE to scripts/)
│
├── business_sample.docx          # Sample files (MOVE to demo_data/ or DELETE)
├── nursing_sample.docx           # Sample files (MOVE to demo_data/ or DELETE)
├── test_server.log               # Temp log file (DELETE)
├── pr_comments_scratch.md        # Scratch file (DELETE)
└── course_record_updater_text_only.zip  # OLD artifact (DELETE)
```

---

## 📋 Migration Strategy

### Phase 1: Preparation
1. **Create New Directory Structure**
   ```bash
   mkdir -p src/{services,database,models,utils,cli}
   mkdir -p config
   mkdir -p build
   mkdir -p data/databases
   ```

2. **Update .gitignore**
   - Add `build/` to ignore list
   - Update paths for moved artifacts

### Phase 2: Move Source Code
1. **Move Service Modules** → `src/services/`
2. **Move Database Modules** → `src/database/`
3. **Move Models** → `src/models/`
4. **Move Utilities** → `src/utils/`
5. **Move CLI** → `src/cli/`
6. **Move Core App Files** → `src/`
7. **Move Existing Packages** → `src/`

### Phase 3: Move Configuration
1. **Move Config Files** → `config/`
2. **Update Configuration Paths** in:
   - CI/CD workflows (`.github/workflows/*.yml`)
   - Scripts
   - Docker configuration

### Phase 4: Move Build Artifacts
1. **Move Build/Report Files** → `build/`
2. **Update Build Scripts**

### Phase 5: Move Data Files
1. **Move Database Files** → `data/databases/`
2. **Update Database Paths** in:
   - `src/database/database_sqlite.py`
   - `src/utils/constants.py`
   - Test configuration

### Phase 6: Update Imports
1. **Update All Import Statements**:
   - `import api_routes` → `from src import api_routes`
   - `import auth_service` → `from src.services import auth_service`
   - `import models` → `from src.models import models`
   - etc.

2. **Update sys.path Modifications** in:
   - `app.py`
   - Test files
   - Scripts

### Phase 7: Update Configuration References
1. **pytest.ini** → Update `pythonpath`, `testpaths`
2. **sonar-project.properties** → Update `sonar.sources`, `sonar.tests`
3. **.coveragerc** → Update `source` paths
4. **Dockerfile** → Update COPY commands
5. **CI/CD workflows** → Update working directories

### Phase 8: Cleanup
1. Delete temporary files
2. Consolidate archive directories
3. Clean up build artifacts
4. Update documentation

### Phase 9: Verification
1. Run all tests: `pytest`
2. Check imports: `python -m src.app`
3. Verify CI/CD pipeline
4. Run coverage analysis
5. Test Docker build

---

## 🚨 Critical Files Requiring Updates

### Python Files (Import Updates Required)
- **Every `.py` file** will need import path updates
- Priority files:
  - `src/app.py`
  - `tests/conftest.py`
  - All test files
  - All service files

### Configuration Files
- `pytest.ini` - Python path and test discovery
- `sonar-project.properties` - Source and test paths
- `.coveragerc` - Source paths for coverage
- `.github/workflows/*.yml` - All CI/CD workflows
- `Dockerfile` - Copy commands and working directory

### Scripts
- `scripts/*.py` - Any that import from main codebase
- Shell scripts with hardcoded paths

---

## ⚠️ Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking imports | High | Test thoroughly, use IDE refactoring tools |
| CI/CD failures | High | Update all workflow files before merge |
| Database path issues | Medium | Use environment variables, update constants |
| Lost files | Low | Work in feature branch, comprehensive testing |
| Merge conflicts | Medium | Coordinate with team, do in low-activity period |

---

## 🎯 Recommended Execution Order

1. **Create feature branch**: `feat/reorganize-repository-structure`
2. **Create new directory structure**
3. **Start with small, testable moves**:
   - Move `utils/` first (low coupling)
   - Move `models/` second
   - Move `database/` third
   - Move `services/` fourth
   - Move `app.py` and `api_routes.py` last
4. **Update imports incrementally** after each move
5. **Run tests after each phase**
6. **Update configs once moves are complete**
7. **Final verification and cleanup**

---

## 🛠️ Tools to Use

- **IDE Refactoring**: Use PyCharm/VSCode "Move" refactoring to update imports automatically
- **grep/ripgrep**: Find all import statements to verify updates
- **pytest**: Verify tests pass after each phase
- **git**: Use feature branch, commit after each successful phase

---

## 📝 Post-Migration Tasks

1. Update `README.md` with new structure
2. Update `CONTRIBUTING.md` (if exists) with new paths
3. Update developer onboarding docs
4. Create `src/README.md` explaining module organization
5. Archive old documentation referencing old paths

---

## 🔄 Alternative: Gradual Migration

If full migration is too risky, consider:

1. **New code in `src/`** - Start writing new modules in proper location
2. **Opportunistic moves** - Move files when touching them for other changes
3. **Module-by-module** - Migrate one logical module at a time over several PRs

---

## ✅ Success Criteria

- [ ] All source code in `src/` directory
- [ ] Clean root directory (< 20 files at root level)
- [ ] All tests passing
- [ ] CI/CD pipeline working
- [ ] Docker build successful
- [ ] Coverage reports generating correctly
- [ ] No broken imports
- [ ] Documentation updated
