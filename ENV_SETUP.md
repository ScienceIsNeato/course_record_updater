# Environment Setup Guide

## Quick Start

### For New Developers

1. Copy the template to create your local environment file:
   ```bash
   cp .envrc.template .envrc
   ```

2. Add your secrets to `.envrc`:
   ```bash
   # Add after the source line:
   export SONAR_TOKEN="your-token-here"
   export SAFETY_API_KEY="your-key-here"
   export GITHUB_PERSONAL_ACCESS_TOKEN="your-token-here"
   ```

3. Load the environment (if using direnv, it loads automatically):
   ```bash
   source .envrc
   ```

## How It Works

### Two-File Approach

**`.envrc.template`** (version controlled):
- Contains all environment logic
- Defines dev/e2e/ci configurations
- Safe to commit (no secrets)

**`.envrc`** (gitignored):
- Sources `.envrc.template`
- Adds your personal secrets
- Never committed

### Environment Selection

The `APP_ENV` variable controls which environment is active:

| Environment | Port | Database | Use Case |
|-------------|------|----------|----------|
| `dev` | 3001 | `course_records_dev.db` | Local development |
| `e2e` | 3002 | `course_records_e2e.db` | E2E testing |
| `ci` | 3003 | `course_records_ci.db` | CI pipeline |

### Usage Examples

**Development (default)**:
```bash
./restart_server.sh dev
# Starts on port 3001 with dev database
```

**E2E Testing**:
```bash
./run_uat.sh
# Automatically sets APP_ENV=e2e, uses port 3002
```

**Manual Environment Override**:
```bash
export APP_ENV="e2e"
source .envrc
./restart_server.sh e2e
```

## CI Environment

In CI (GitHub Actions):
- `APP_ENV=ci` set in workflow environment variables
- `.envrc.template` is sourced directly
- Secrets provided via GitHub Secrets
- No `.envrc` file needed

## Troubleshooting

**"Neither .envrc nor .envrc.template found"**
- Solution: Copy `.envrc.template` to `.envrc`

**"Port already in use"**
- Solution: Check which environment is running: `lsof -i :3001 :3002 :3003`
- Each environment uses a different port to avoid conflicts

**Secrets not loading**
- Solution: Verify `.envrc` sources the template and defines secrets after
- Check: `echo $SONAR_TOKEN` should show your token

## File Structure

```
.envrc.template          # Logic (committed)
.envrc                   # Secrets (gitignored)
.gitignore               # Excludes .envrc
restart_server.sh        # Sources .envrc or .envrc.template
run_uat.sh              # Sets APP_ENV=e2e
```

