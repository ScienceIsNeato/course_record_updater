# Smoke Testing Guide

## Overview

Smoke testing ensures that your current feature works end-to-end without running the full integration test suite during development.

## When to Smoke Test

✅ **Before committing feature work**
✅ **After making significant changes to core functionality**
✅ **When working on import/export flows**
✅ **After updating database schemas or API endpoints**

## Quick Smoke Tests by Feature

### 🔥 Import System
```bash
# Test CLI import (fastest)
python import_cli.py --file test_data/cei_sample.xlsx --dry-run --verbose

# Test web import (comprehensive)
./restart_server.sh
# Navigate to http://localhost:3001
# Upload test file with dry-run enabled
```

### 🔥 Database Operations
```bash
# Test Firestore connection
python -c "from database_service import db; print('✅ Database connected')"

# Test basic CRUD
python -c "
from database_service_extended import create_course, get_course_by_id
course_id = create_course({'course_number': 'TEST-101', 'course_title': 'Test Course'})
course = get_course_by_id(course_id)
print(f'✅ CRUD working: {course}')
"
```

### 🔥 Web Interface
```bash
# Start server and check basics
./restart_server.sh
curl -s http://localhost:3001 | grep -q "CEI Course Admin" && echo "✅ Web server working"

# Check API health
curl -s http://localhost:3001/api/health | jq .
```

### 🔥 Data Models & Validation
```bash
# Run unit tests for current models
python -m pytest tests/unit/test_models.py -v

# Test term generation
python -c "from term_utils import get_allowed_terms; print('✅ Terms:', len(get_allowed_terms()))"
```

## Feature-Specific Smoke Tests

### Working on Import Features
1. **Unit test the specific adapter**:
   ```bash
   python -m pytest tests/unit/test_*_adapter.py -v
   ```

2. **Test CLI with your data**:
   ```bash
   python import_cli.py --file your_test_file.xlsx --dry-run --verbose
   ```

3. **Quick web test**:
   - Upload file with dry-run
   - Check validation results
   - Verify conflict resolution options

### Working on Database Features
1. **Test your specific database functions**:
   ```bash
   python -m pytest tests/unit/test_models.py::TestYourModel -v
   ```

2. **Integration smoke test**:
   ```bash
   python -m pytest tests/integration/test_database_service_integration.py::test_your_feature -v
   ```

### Working on API Features
1. **Test specific endpoints**:
   ```bash
   curl -X POST http://localhost:3001/api/your-endpoint -d '{"test": "data"}'
   ```

2. **Frontend integration**:
   - Check browser console for errors
   - Test form submissions
   - Verify AJAX responses

## Automated Smoke Testing

### Quick Health Check
```bash
# Comprehensive health check (30 seconds)
./check_frontend.sh
```

### Targeted Smoke Tests
```bash
# Run smoke tests for specific areas
python -m pytest tests/integration/test_frontend_smoke.py::TestFrontendSmoke::test_your_area -v
```

## Best Practices

### ✅ Do This
- Run unit tests first (3 seconds)
- Test your specific feature manually
- Use dry-run mode for destructive operations
- Check browser console for JavaScript errors
- Verify API responses with curl/Postman

### ❌ Avoid This
- Running full integration suite during development
- Skipping smoke tests before commits
- Testing only happy path scenarios
- Ignoring error messages in logs

## Integration with Development Workflow

### Pre-Commit (Automated)
- Unit tests run automatically
- Code formatting and linting
- Basic validation checks

### During Development (Manual Smoke Testing)
- Test your specific feature end-to-end
- Verify edge cases and error handling
- Check UI/UX for your changes

### CI Pipeline (Comprehensive)
- All unit tests + integration tests
- Cross-browser testing (if applicable)
- Performance and security validation

## Troubleshooting Common Issues

### Import Not Working
```bash
# Check file format
file your_file.xlsx

# Test adapter directly
python -c "from adapters.cei_excel_adapter import parse; print(parse('your_file.xlsx'))"

# Check database connection
python -c "from database_service import db; print('DB Status:', db._client)"
```

### Web Interface Issues
```bash
# Check server logs
./tail_logs.sh

# Verify static assets
curl -I http://localhost:3001/static/script.js

# Test API endpoints
curl http://localhost:3001/api/health
```

### Database Issues
```bash
# Check Firestore emulator
curl http://localhost:8086

# Test basic operations
python -c "from database_service import db; print('Collections:', list(db.collections()))"
```

This approach gives you confidence in your changes without the overhead of running the full test suite during development.
