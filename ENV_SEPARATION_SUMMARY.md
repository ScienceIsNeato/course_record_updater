# Environment Separation - Quick Summary

## TL;DR
We're splitting into 3 environments so E2E tests don't stomp on dev work:
- **DEV** (port 3001): Your active development
- **E2E** (port 3002): Automated tests
- **CI** (port 3003): GitHub Actions

**Time to implement MVP**: ~1 hour  
**Benefit**: Work and test simultaneously without conflicts

---

## The Problem You Identified

> "E2E tests are going to stomp over whatever I might be doing in dev, or interrupt other agents"

**Current State**:
```
You working on dev    →  Start E2E tests  →  💥 Server restarts on 3001
                                           →  💥 Dev database gets nuked
                                           →  💥 Lost your work
```

**Desired State**:
```
You working on dev (3001)  →  Still running, untouched
E2E tests (3002)           →  Separate server, separate DB
CI pipeline (3003)         →  Completely isolated
```

---

## Three-Environment Model

| Environment | Port | Database | Purpose | Lifecycle |
|-------------|------|----------|---------|-----------|
| **DEV** | 3001 | `course_records_dev.db` | Active development | Manual, persistent |
| **E2E** | 3002 | `course_records_e2e.db` | Automated tests | Auto-managed, fresh each run |
| **CI** | 3003 | `course_records_ci.db` | GitHub Actions | Ephemeral, isolated |

---

## Implementation Checklist (MVP - 1 hour)

### Step 1: Update Single .envrc File (5 min)
**Key Change**: ONE `.envrc` file controlled by `APP_ENV` variable

```bash
# Edit .envrc - update the environment-specific configuration section:

# Environment-specific configuration
export APP_ENV="${APP_ENV:-dev}"  # Defaults to dev

# Derive port and database based on APP_ENV
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

# Always DEBUG logging (helps troubleshoot E2E and CI failures)
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"

echo "🌍 Environment: $APP_ENV | Port: $COURSE_RECORD_UPDATER_PORT | DB: $DATABASE_URL"
```

**Note**: Keep your existing secrets (SONAR_TOKEN, etc.) - don't modify those lines

**Note**: Keep LOG_LEVEL=DEBUG for all environments (helps debug failures)

### Step 2: Update `run_uat.sh` (10 min)
Update to explicitly use E2E environment:
```bash
#!/bin/bash

# Clear E2E database (fresh start)
rm -f course_records_e2e.db

# Seed E2E database with E2E environment
export APP_ENV="e2e"
source .envrc
python scripts/seed_db.py

# Start server explicitly in E2E mode
./restart_server.sh e2e  # <-- Pass "e2e" argument
```

**Key**: Pass explicit environment argument to `restart_server.sh`

### Step 3: Update `restart_server.sh` (5 min)
**Make it require explicit environment argument**:
```bash
#!/bin/bash

# Require environment argument (dev, e2e, or ci)
if [ -z "$1" ]; then
    echo "❌ Error: Environment argument required"
    echo "Usage: $0 <env>"
    echo "  <env> = dev | e2e | ci"
    exit 1
fi

# Set environment and source .envrc
export APP_ENV="$1"
source .envrc

echo "🚀 Starting $APP_ENV server on port $COURSE_RECORD_UPDATER_PORT"

# Kill existing servers on this port, then start
lsof -ti:$COURSE_RECORD_UPDATER_PORT | xargs kill -9 2>/dev/null || true
python app.py
```

**Key**: Requires explicit argument - prevents accidents

### Step 4: Test Locally (10 min)
```bash
# Terminal 1: Start dev server
./restart_server.sh dev
# Should start on port 3001

# Terminal 2: Run E2E tests
./run_uat.sh
# Should start on port 3002 (run_uat.sh passes "e2e" to restart_server.sh)

# Verify both running
lsof -i :3001  # Dev server
lsof -i :3002  # E2E server (during test)
```

### Step 5: Update CI (15 min)
Add to `.github/workflows/quality-gate.yml`:
```yaml
env:
  ENVIRONMENT: ci
  DATABASE_URL: sqlite:///course_records_ci.db
  COURSE_RECORD_UPDATER_PORT: 3003
```

### Step 6: Documentation (10 min)
- [x] Created `ENVIRONMENT_SEPARATION_PLAN.md` (full design)
- [x] Updated `NEXT_BACKLOG.md` (Priority 0)
- [ ] Update README with environment setup instructions
- [ ] Add troubleshooting guide

---

## How to Use After Implementation

### Development
```bash
# Start dev server (explicit)
./restart_server.sh dev  # Starts on 3001
```

### E2E Testing
```bash
# Just run the UAT script
./run_uat.sh  # Automatically passes "e2e" to restart_server.sh, runs on port 3002
```

### Manual Environment Selection
```bash
# Explicit environment argument required
./restart_server.sh dev   # Port 3001, course_records_dev.db
./restart_server.sh e2e   # Port 3002, course_records_e2e.db
./restart_server.sh ci    # Port 3003, course_records_ci.db
```

### CI (Automatic)
- GitHub Actions automatically uses CI environment
- No manual intervention needed

---

## Benefits

### Immediate
- ✅ No more E2E tests interrupting dev work
- ✅ Multiple agents can work simultaneously
- ✅ Test data doesn't pollute dev database
- ✅ Port conflicts resolved

### Future
- ✅ Easy to add staging environment
- ✅ Foundation for automated deployments
- ✅ Clear separation for production
- ✅ Supports team growth (multiple developers)

---

## Next Steps

1. **Review this design** - Does it solve your problem?
2. **Approve implementation** - Ready to start Step 1?
3. **Incremental rollout** - Can implement steps 1-4 today, 5-6 later

Would you like me to start implementing Step 1 (create environment files)?

