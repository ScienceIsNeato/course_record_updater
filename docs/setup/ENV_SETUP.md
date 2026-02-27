# Environment Setup Guide

## Quick Start

### For New Developers

1. Copy the template to create your local environment file:

   ```bash
   cp .envrc.template .envrc
   ```

2. Add your secrets to `.envrc`:

   ```bash
   # Uncomment and set real values in .envrc (not committed):
   export ETHEREAL_USER="your-username@ethereal.email"
   export ETHEREAL_PASS="your-password"
   export BREVO_API_KEY="your-brevo-api-key"
   export BREVO_SENDER_EMAIL="noreply@yourdomain.com"
   export BREVO_SENDER_NAME="Your App Name"

   # Optional (for quality gates):
   export SONAR_TOKEN="your-token-here"
   export SAFETY_API_KEY="your-key-here"
   export GITHUB_PERSONAL_ACCESS_TOKEN="your-token-here"
   ```

3. Load the environment (if using direnv, it loads automatically):
   ```bash
   source .envrc
   ```

## Environment Variable Pattern

### Important: Template File Pattern

The `.envrc.template` file follows a strict pattern to prevent credential override issues:

**✅ DO: Export variables with valid default values**

```bash
export DATABASE_URL="sqlite:///course_records.db"
export LOG_LEVEL="INFO"
export ETHEREAL_SMTP_HOST="smtp.ethereal.email"  # Valid default
```

**✅ DO: Comment out variables that require user-specific values**

```bash
# export BREVO_API_KEY="your-api-key-here"
# export ETHEREAL_USER="your-username@ethereal.email"
```

**❌ DON'T: Export placeholder values that would break if used**

```bash
export ETHEREAL_USER="your-username@ethereal.email"  # BAD!
# This placeholder would override real credentials if template is sourced
```

### Why This Matters

When bash sources a file, every `export` statement **overwrites** that variable. If CI sets credentials from GitHub secrets, then sources `.envrc.template` with placeholder exports, the placeholders overwrite the real credentials.

**Solution**: Only export valid defaults in the template. Comment out user-specific values.

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

| Environment | Port | Database                | Use Case                 |
| ----------- | ---- | ----------------------- | ------------------------ |
| `dev`       | 3001 | `course_records_dev.db` | Local development        |
| `e2e`       | 3002 | `course_records_e2e.db` | E2E testing (local & CI) |

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

## CI Environment Configuration

### GitHub Actions Setup

In CI (GitHub Actions), environment variables are handled differently to prevent credential override issues:

#### 1. Add Secrets to GitHub

Navigate to: Repository → Settings → Secrets and variables → Actions → New repository secret

Required secrets:

- `ETHEREAL_USER`: Your Ethereal email username (for E2E tests)
- `ETHEREAL_PASS`: Your Ethereal email password (for E2E tests)
- `BREVO_API_KEY`: Your Brevo API key (if testing real emails)
- `BREVO_SENDER_EMAIL`: Verified sender email in Brevo
- `BREVO_SENDER_NAME`: Sender name for emails

#### 2. Workflow Configuration Pattern

**CRITICAL**: Export credentials **BEFORE** sourcing `.envrc.template`:

```yaml
- name: Run E2E Tests
  run: |
    # 1. Export credentials from GitHub secrets FIRST
    export ETHEREAL_USER="${{ secrets.ETHEREAL_USER }}"
    export ETHEREAL_PASS="${{ secrets.ETHEREAL_PASS }}"

    # 2. THEN source template (won't override because credentials are commented out)
    source .envrc.template

    # 3. Run tests
    python scripts/ship_it.py --checks e2e
```

**❌ WRONG ORDER (causes credential override)**:

```yaml
- name: Run E2E Tests (BROKEN)
  run: |
    source .envrc.template  # Template might have placeholder exports
    export ETHEREAL_USER="${{ secrets.ETHEREAL_USER }}"  # Too late!
```

#### 3. Why Order Matters

- When bash sources a file, every `export` statement **overwrites** existing variables
- If template has `export ETHEREAL_USER="placeholder"`, it overwrites real credentials
- Solution: Comment out credentials in template, export real values first

### Script Behavior in CI

`run_uat.sh` detects CI environment and handles credentials appropriately:

```bash
# Only sources template if credentials not already set
if [ -f ".envrc.template" ] && [ -z "$ETHEREAL_USER" ]; then
    source .envrc.template
elif [ "${CI:-false}" = "true" ]; then
    echo "CI detected with credentials already set, skipping template"
fi
```

This ensures credentials from GitHub secrets are never overridden.

## Troubleshooting

**"Neither .envrc nor .envrc.template found"**

- Solution: Copy `.envrc.template` to `.envrc`

**"Port already in use"**

- Solution: Check which environment is running: `lsof -i :3001 :3002`
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
