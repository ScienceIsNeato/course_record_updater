# Environment Separation Plan

## Problem Statement
Currently, all development activities (manual dev, E2E tests, CI runs, agent work) share:
- Single Flask server instance (port 3001)
- Single SQLite database (`course_records.db`)
- Single set of environment variables

This causes:
- E2E tests restart server, interrupting active development
- Test data pollution in dev database
- Agent work conflicts with manual testing
- No isolation for CI/CD pipeline

## Design Principles
1. **Lightweight & Incremental**: Start simple, add complexity only as needed
2. **Environment Variables Drive Everything**: Single source of truth for configuration
3. **Forward-Thinking**: Lay groundwork for automated deployments
4. **MVP First**: Get basic separation working, iterate on sophistication

---

## Phase 1: Three-Environment Model (MVP) 🎯

### Environments

#### 1. **DEV** (Manual Development)
- **Purpose**: Active development, manual testing, debugging
- **Database**: `course_records_dev.db`
- **Port**: `3001` (current default)
- **Server**: Manual start/stop via `./restart_server.sh`
- **When**: Developer is actively coding
- **Characteristics**: 
  - Persistent data (don't nuke DB on every restart)
  - Long-running server process
  - Manual control

#### 2. **E2E** (End-to-End Testing)
- **Purpose**: Automated browser tests, UAT validation
- **Database**: `course_records_e2e.db` (nuked on each test run)
- **Port**: `3002`
- **Server**: Managed by `run_uat.sh` (auto-start/stop)
- **When**: Running E2E test suite
- **Characteristics**:
  - Fresh database on every run (seeded via `seed_db.py`)
  - Ephemeral server (killed after tests)
  - Fully automated

#### 3. **CI** (Continuous Integration)
- **Purpose**: GitHub Actions, automated quality gates
- **Database**: `course_records_ci.db` (ephemeral, in-memory if possible)
- **Port**: `3003`
- **Server**: Managed by CI pipeline
- **When**: PR checks, merge validations
- **Characteristics**:
  - Completely isolated from local development
  - Disposable (created/destroyed per CI run)
  - No manual interaction

### Future: **PROD** (Production)
- **Purpose**: Live user-facing application
- **Database**: Hosted database (managed backups)
- **Port**: Standard HTTPS (443)
- **Server**: Managed by hosting platform (auto-scaling, health checks)
- **When**: Always running
- **Characteristics**:
  - High availability, monitoring, security hardening
  - **NOT PART OF MVP** - deferred to Priority 8

---

## Implementation Strategy

### Step 1: Environment Variable Schema ✅ NEXT

**File**: Single `.envrc` file with runtime environment selection

```bash
# .envrc (single file, always sourced)
# Path Management
export AGENT_HOME="/path/to/project"

# Shared secrets (gitignored, all environments)
export SONAR_TOKEN="your-token-here"
export SAFETY_API_KEY="your-key-here"
export GITHUB_PERSONAL_ACCESS_TOKEN="your-token-here"

# Environment-specific defaults (can be overridden at runtime)
export APP_ENV="${APP_ENV:-dev}"  # dev, e2e, or ci

# Derive environment-specific values based on APP_ENV
case "$APP_ENV" in
  dev)
    export DATABASE_URL="sqlite:///course_records_dev.db"
    export COURSE_RECORD_UPDATER_PORT="3001"
    ;;
  e2e)
    export DATABASE_URL="sqlite:///course_records_e2e.db"
    export COURSE_RECORD_UPDATER_PORT="3002"
    ;;
  ci)
    export DATABASE_URL="sqlite:///course_records_ci.db"
    export COURSE_RECORD_UPDATER_PORT="3003"
    ;;
esac

# Common settings for all environments
export DATABASE_TYPE="sqlite"
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"  # Always DEBUG for troubleshooting

echo "🌍 Environment: $APP_ENV | Port: $COURSE_RECORD_UPDATER_PORT | DB: $DATABASE_URL"
```

**Strategy**:
- **Single `.envrc` file** - no multiple files to manage
- **`APP_ENV` controls everything** - set once at runtime
- **Scripts set `APP_ENV` before sourcing** `.envrc`
- **All variables overridable** - flexibility for edge cases
- **Always DEBUG logging** - helps debug failures in all environments

### Step 2: Update `run_uat.sh` to Use E2E Environment ✅ NEXT

```bash
#!/bin/bash

# Clear E2E database (fresh slate)
rm -f course_records_e2e.db

# Seed E2E database (sets APP_ENV=e2e internally)
export APP_ENV="e2e"
source .envrc
python scripts/seed_db.py

# Start server on E2E port (3002)
./restart_server.sh e2e

# Run E2E tests against E2E server
pytest tests/e2e/ -m e2e

# Cleanup
kill_server
```

**Benefits**:
- Single `.envrc` file, controlled by `APP_ENV`
- E2E tests no longer interfere with dev server on 3001
- Developer can keep working while tests run
- Fresh database every time (no test pollution)

### Step 3: Update `restart_server.sh` to Require Environment Argument

**New Signature**: `./restart_server.sh <env>` where `<env>` is `dev`, `e2e`, or `ci`

```bash
#!/bin/bash

# Require environment argument
if [ -z "$1" ]; then
    echo "❌ Error: Environment argument required"
    echo "Usage: $0 <env>"
    echo "  <env> = dev | e2e | ci"
    exit 1
fi

ENV_ARG="$1"

# Validate environment
if [[ ! "$ENV_ARG" =~ ^(dev|e2e|ci)$ ]]; then
    echo "❌ Error: Invalid environment '$ENV_ARG'"
    echo "Valid: dev, e2e, ci"
    exit 1
fi

# Set environment BEFORE sourcing .envrc
export APP_ENV="$ENV_ARG"

# Source .envrc (which reads APP_ENV)
source .envrc

echo "🚀 Starting $APP_ENV server on port $COURSE_RECORD_UPDATER_PORT"
echo "   Database: $DATABASE_URL"

# Kill existing servers on this port
lsof -ti:$COURSE_RECORD_UPDATER_PORT | xargs kill -9 2>/dev/null || true

# Start server
python app.py
```

**Benefits**:
- **Explicit environment** - no ambiguity about which env is running
- **Prevents accidents** - can't accidentally start wrong environment
- **Clear errors** - fails fast if environment not specified
- **Self-documenting** - usage is obvious from error message

### Step 4: CI Pipeline Environment Setup

**File**: `.github/workflows/quality-gate.yml`

```yaml
name: Quality Gate

on: [pull_request, push]

jobs:
  test:
    runs-on: ubuntu-latest
    
    env:
      ENVIRONMENT: ci
      DATABASE_URL: sqlite:///course_records_ci.db
      COURSE_RECORD_UPDATER_PORT: 3003
      
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      
      - name: Run quality gates
        run: python scripts/ship_it.py --validation-type PR
      
      - name: Run E2E tests
        run: |
          source .envrc.ci
          ./run_uat.sh
```

**Benefits**:
- CI runs never conflict with local development
- Isolated database per CI run
- Same test suite runs locally and in CI

---

## File Structure

```
/Users/pacey/Documents/SourceCode/course_record_updater/
├── .envrc                  # Single environment file (uses APP_ENV)
├── course_records_dev.db   # Dev database (persistent)
├── course_records_e2e.db   # E2E database (ephemeral)
├── course_records_ci.db    # CI database (ephemeral)
├── restart_server.sh       # Environment-aware server script
├── run_uat.sh             # E2E test runner (sets APP_ENV=e2e)
└── scripts/
    └── ship_it.py         # Quality gate runner
```

**Key Simplification**: Just ONE `.envrc` file, controlled by `APP_ENV` variable

---

## Migration Path (Incremental Steps)

### ✅ Step 1: Update Single .envrc File (5 minutes)
- [ ] Add `APP_ENV` variable with default "dev"
- [ ] Add `case` statement to set port/DB based on `APP_ENV`
- [ ] Keep all existing secrets/tokens
- [ ] Keep LOG_LEVEL="DEBUG" for all environments
- [ ] Update `.gitignore` to exclude all `course_records_*.db` files

### ✅ Step 2: Update `run_uat.sh` (10 minutes)
- [ ] Add `export APP_ENV="e2e"` at the top (before sourcing .envrc)
- [ ] Verify port isolation (should start on 3002)
- [ ] Test that dev server on 3001 stays running

### ✅ Step 3: Update `restart_server.sh` (5 minutes)
- [ ] Read PORT from environment variable
- [ ] Read DATABASE_URL from environment variable
- [ ] Add logging to show which env is active

### ✅ Step 4: Test Locally (10 minutes)
- [ ] Start dev server: `source .envrc.dev && ./restart_server.sh`
- [ ] Verify dev server runs on 3001 with dev database
- [ ] Run E2E tests: `./run_uat.sh`
- [ ] Verify E2E server runs on 3002 with separate database
- [ ] Confirm both can run simultaneously

### ⏳ Step 5: Update CI Pipeline (15 minutes)
- [ ] Add `export APP_ENV="ci"` to GitHub Actions workflow
- [ ] Source `.envrc` in CI pipeline
- [ ] Test PR run to verify isolation

### ⏳ Step 6: Documentation (10 minutes)
- [ ] Update README with environment setup instructions
- [ ] Update NEXT_BACKLOG.md with completed tasks
- [ ] Add troubleshooting guide for port conflicts

**Total MVP Time: ~1 hour**

---

## Testing the Separation

### Manual Test Plan

1. **Start Dev Server**
   ```bash
   source .envrc.dev
   ./restart_server.sh
   # Should see: Starting on port 3001 with dev database
   ```

2. **In Separate Terminal, Run E2E Tests**
   ```bash
   ./run_uat.sh
   # Should see: Starting on port 3002 with e2e database
   ```

3. **Verify Isolation**
   ```bash
   lsof -i :3001  # Should show dev server
   lsof -i :3002  # Should show E2E server (during test run)
   ls -la course_records*.db  # Should show both databases
   ```

4. **Verify No Interference**
   - Make changes in dev database via browser (http://localhost:3001)
   - Run E2E tests (which nuke E2E database)
   - Verify dev changes still exist

---

## Benefits of This Approach

### Immediate Wins
- ✅ E2E tests no longer interrupt development
- ✅ Multiple agents can work simultaneously (different environments)
- ✅ Test data isolation (no more dev DB pollution)
- ✅ Port conflict resolution

### Future-Ready
- ✅ Clear path to staging environment (add `.envrc.staging`)
- ✅ Foundation for automated deployments
- ✅ Easy to add environment-specific configurations
- ✅ Supports multiple developers with different local ports

### Low Complexity
- ✅ No Docker required (lightweight)
- ✅ No complex orchestration (just bash scripts)
- ✅ Works on any OS that supports environment variables
- ✅ Easy to understand and debug

---

## Future Enhancements (Post-MVP)

### Phase 2: Staging Environment
- Add `.envrc.staging` for pre-production testing
- Deploy to hosted instance for stakeholder UAT
- Automated deployment on main branch merge

### Phase 3: Production Environment
- Hosted database with backups
- Domain, SSL, CDN
- Monitoring, alerting, auto-scaling
- Blue-green or canary deployments

### Phase 4: Developer Experience
- CLI tool: `./env.sh dev` to switch environments
- Environment status indicator in terminal prompt
- Automatic environment detection in scripts
- Health check dashboard showing all environments

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Developers forget to source right env | Make scripts source env automatically |
| Port conflicts with other apps | Use configurable ports, add conflict detection |
| Shared secrets in multiple files | Use `.envrc.shared` for common secrets |
| CI environment drift | Pin dependency versions, use same seed script |
| Lost work from wrong env | Add environment indicator to UI/terminal |

---

## Success Criteria

- [ ] Dev server on 3001, E2E on 3002 run simultaneously without conflict
- [ ] E2E tests complete without affecting dev database
- [ ] CI runs use isolated environment (3003)
- [ ] Documentation updated with environment setup instructions
- [ ] All tests pass in all three environments

