# Agent Lessons Learned

## Quality Gate Execution Best Practices

### ✅ CORRECT: Use Appropriate Validation Type
```bash
# Fast commit validation (default - excludes slow security & sonar)
python scripts/ship_it.py

# Full PR validation (comprehensive - includes all checks)
python scripts/ship_it.py --validation-type PR
```

### ❌ INCORRECT: Unnecessarily Enumerate Individual Checks
```bash
# DON'T do this unless you specifically need only certain checks
python scripts/ship_it.py --checks black isort lint tests coverage security types
```

### When to Use Specific Checks
Only specify `--checks` when you need targeted validation:
- `--checks tests` - Quick test-only run during development
- `--checks black isort` - Format-only fixes
- `--checks tests coverage` - Test validation cycle

### Updated Default Behavior (2025)
- **No flags** = Fast commit validation (excludes security & sonar for speed)
- **`--validation-type PR`** = Comprehensive validation with all checks
- **Fail-fast always enabled** = Immediate feedback on first failure
- **78s time savings** with commit validation vs PR validation

### Validation Type Selection
- **Commit validation**: Use during development for rapid feedback cycles
- **PR validation**: Use before creating pull requests for comprehensive quality assurance
- **Specific checks**: Use for targeted fixes or debugging specific issues

## Key Insight
The script now optimizes for development speed by default while maintaining comprehensive validation options. The fail-fast behavior is always enabled, and validation types allow developers to choose the appropriate level of checking based on context.

## Server Management Best Practices

### ✅ CORRECT: Use the Restart Script
```bash
# Proper server startup with all environment setup
./restart_server.sh
```

### ❌ INCORRECT: Manual Python Execution
```bash
# DON'T do this - bypasses environment setup and port management
python app.py

# DON'T do this - misses virtual environment activation
cd /path/to/project && python app.py &
```

### Why Use `restart_server.sh`?
The restart script provides:
- **Environment variable loading** from `.envrc` 
- **Virtual environment activation**
- **Port conflict resolution** (kills existing processes on port 3001)
- **Firestore emulator verification** (starts if needed)
- **Proper logging** to `logs/server.log`
- **Non-blocking startup** with success verification
- **Consistent behavior** across development environments

### Flask Threading Issues (Fixed 2025-09-17)

**Problem**: Database operations failed with `signal only works in main thread of the main interpreter`

**Root Cause**: The `db_operation_timeout` context manager used `signal.alarm()` for timeouts, but Flask request handlers run in separate threads where signals don't work.

**Solution**: Removed signal-based timeout mechanism from database operations:
```python
# BEFORE (broken in Flask threads):
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(seconds)

# AFTER (thread-safe):
# Signal-based timeout doesn't work in Flask request threads
# For now, just yield without timeout enforcement
yield
```

**Symptoms to Watch For**:
- API endpoints returning empty results (`count: 0`) despite data existing in database
- Error logs showing `signal only works in main thread` messages
- Database queries working in direct Python scripts but failing in Flask routes

**Prevention**: Avoid using `signal` module in any code that might run in Flask request threads. Use thread-safe alternatives like `threading.Timer` or `concurrent.futures.TimeoutError` if timeouts are needed.

### Session Management Best Practices (Fixed 2025-09-17)

**Problem**: Flask session files were being created in the project root and getting committed to source control.

**Root Cause**: Flask-Session with `SESSION_TYPE = "filesystem"` creates session files in the current directory by default.

**Solution**: Configure a dedicated session directory and add it to `.gitignore`:
```python
# In session_service.py
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "flask_session"  # Dedicated directory
```

```gitignore
# In .gitignore
flask_session/
*flask_session*
```

**Prevention**: Always configure `SESSION_FILE_DIR` when using filesystem sessions, and ensure session directories are in `.gitignore`.

### Dashboard Route Consistency (Fixed 2025-09-17)

**Problem**: Login redirects to `/dashboard` but the actual route is `/api/dashboard`, causing 404 errors.

**Root Cause**: Inconsistent route naming - some code referenced `/dashboard` while the actual route was `/api/dashboard`.

**Solution**: Added a redirect route for consistency:
```python
@app.route("/dashboard")
def dashboard_redirect():
    """Redirect to the API dashboard route for consistency"""
    return redirect(url_for(DASHBOARD_ENDPOINT))
```

**Prevention**: Use `url_for()` with route names instead of hardcoding URLs, and maintain consistent route naming conventions.
