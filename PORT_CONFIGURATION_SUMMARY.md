# Port Configuration - Unified Approach

## Overview
Unified port configuration across all bash scripts using environment-specific variables.

## Environment Variables

### Primary Variables (New Standard)
- `LASSIE_DEFAULT_PORT_DEV="3001"` - Development server port
- `LASSIE_DEFAULT_PORT_E2E="3002"` - E2E test server port  
- `LASSIE_DEFAULT_PORT_CI="3003"` - CI server port (future)

### Removed Legacy Variables
- ~~`DEFAULT_PORT`~~ - Replaced with `LASSIE_DEFAULT_PORT_DEV`
- ~~`COURSE_RECORD_UPDATER_PORT`~~ - No longer needed (greenfield approach)

## Configuration Files

### `.envrc.template`
Template file with port configuration:
```bash
export LASSIE_DEFAULT_PORT_DEV="3001"
export LASSIE_DEFAULT_PORT_E2E="3002"
```

### `.envrc`
Local file (gitignored) that sources template and adds secrets.

## Script Behavior

### `restart_server.sh`
- **Input**: Environment argument (dev|e2e|ci)
- **Behavior**: Automatically selects correct port based on environment:
  - `dev` → Uses `LASSIE_DEFAULT_PORT_DEV` (defaults to 3001)
  - `e2e` → Uses `LASSIE_DEFAULT_PORT_E2E` (defaults to 3002)
  - `ci` → Uses `LASSIE_DEFAULT_PORT_CI` (defaults to 3003)
- **No manual port setting needed**

### `run_uat.sh`
- Reads `LASSIE_DEFAULT_PORT_E2E` (defaults to 3002)
- Calls `./restart_server.sh e2e` (which automatically uses correct port)
- Cleanup uses same env var

### Python Code (`constants.py`)
- `E2E_TEST_PORT = 3002` - Hardcoded constant for Python E2E tests
- Used by `tests/e2e/conftest.py` for `BASE_URL`
- Bash scripts use env vars, Python uses constant

## Design Principles

1. **Single Source of Truth per Language**:
   - Bash scripts: Environment variables
   - Python code: Constants in `constants.py`

2. **Environment-Aware**:
   - Port automatically determined by environment flag
   - No manual port configuration needed

3. **Fallback Defaults**:
   - All env vars have sensible defaults (3001, 3002, 3003)
   - Scripts work even if env vars not set

4. **Consistent Naming**:
   - `LASSIE_DEFAULT_PORT_<ENV>` pattern
   - Clear, descriptive variable names

## Migration Notes

### What Changed
- **Removed**: All legacy port variables (`DEFAULT_PORT`, `COURSE_RECORD_UPDATER_PORT`)
- **Added**: Environment-specific `LASSIE_DEFAULT_PORT_*` variables
- **Updated**: `restart_server.sh` to auto-select port based on environment
- **Updated**: `maintAInability-gate.sh` to use new variables
- **Simplified**: `run_uat.sh` no longer needs to set ports manually

### Greenfield Approach
- No backward compatibility with old variable names
- Clean, consistent naming across all scripts
- Single source of truth per environment

## Testing
```bash
# Development server (port 3001)
./restart_server.sh dev

# E2E test server (port 3002)
./restart_server.sh e2e

# Run UAT tests (automatically uses port 3002)
./run_uat.sh
```

