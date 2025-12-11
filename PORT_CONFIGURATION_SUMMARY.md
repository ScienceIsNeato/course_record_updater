# Port Configuration - Simplified Approach

## Overview
Simplified port configuration with just two environments: dev and e2e.

## Environment Variables

### Port Variables
- `LOOPCLOSER_DEFAULT_PORT_DEV="3001"` - Development server port
- `LOOPCLOSER_DEFAULT_PORT_E2E="3002"` - E2E test server port (local & CI)

### Removed Variables
- ~~`LOOPCLOSER_DEFAULT_PORT_CI`~~ - Removed (CI uses e2e environment)
- ~~`DEFAULT_PORT`~~ - Replaced with `LOOPCLOSER_DEFAULT_PORT_DEV`
- ~~`COURSE_RECORD_UPDATER_PORT`~~ - No longer needed

## Configuration Files

### `.envrc.template`
Template file with port configuration:
```bash
export LOOPCLOSER_DEFAULT_PORT_DEV="3001"
export LOOPCLOSER_DEFAULT_PORT_E2E="3002"
```

### `.envrc`
Local file (gitignored) that sources template and adds secrets.

## Script Behavior

### `restart_server.sh`
- **Input**: Environment argument (dev|e2e)
- **Behavior**: Automatically selects correct port based on environment:
  - `dev` → Uses `LOOPCLOSER_DEFAULT_PORT_DEV` (defaults to 3001)
  - `e2e` → Uses `LOOPCLOSER_DEFAULT_PORT_E2E` (defaults to 3002)
- **No manual port setting needed**

### `run_uat.sh`
- Reads `LOOPCLOSER_DEFAULT_PORT_E2E` (defaults to 3002)
- Calls `./restart_server.sh e2e` (which automatically uses correct port)
- Cleanup uses same env var

### Python Code (`constants.py`)
- `E2E_TEST_PORT = 3002` - Hardcoded constant for Python E2E tests
- Used by `tests/e2e/conftest.py` for `BASE_URL`
- Bash scripts use env vars, Python uses constant

## Design Principles

1. **Two Environments Only**:
   - `dev`: Local development (port 3001)
   - `e2e`: E2E tests, works identically in local and CI (port 3002)

2. **Single Source of Truth per Language**:
   - Bash scripts: Environment variables
   - Python code: Constants in `constants.py`

3. **Environment-Aware**:
   - Port automatically determined by environment flag
   - No manual port configuration needed

4. **Fallback Defaults**:
   - All env vars have sensible defaults (3001, 3002)
   - Scripts work even if env vars not set

5. **Consistent Naming**:
   - `LOOPCLOSER_DEFAULT_PORT_<ENV>` pattern
   - Clear, descriptive variable names

## Why No Separate CI Environment?

- **CI runs in isolation**: No port conflicts with other processes
- **Consistency**: E2E tests should behave identically locally and in CI
- **Simplicity**: Fewer environments = less confusion
- **No need**: CI doesn't need a different port than E2E tests

## Testing

```bash
# Development server (port 3001)
./restart_server.sh dev

# E2E test server (port 3002) - works locally
./restart_server.sh e2e

# Run UAT tests (automatically uses port 3002)
./run_uat.sh

# CI also uses e2e environment (port 3002)
# No special CI configuration needed
```

## Migration from 3-Environment Setup

### What Changed
- **Removed**: `LOOPCLOSER_DEFAULT_PORT_CI` and CI environment
- **Simplified**: `restart_server.sh` now only handles dev and e2e
- **Updated**: All documentation to reflect 2-environment approach
- **CI**: Now uses e2e environment instead of separate ci environment

### Benefits
- Simpler mental model (2 environments instead of 3)
- E2E tests work identically everywhere
- No port confusion (what is 3003 for anyway?)
- Less configuration to maintain
