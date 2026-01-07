# E2E Test Failure Analysis - 2026-01-07

## Status: INVESTIGATING

### **Problem Summary**

E2E tests are failing to authenticate program admin user despite:
- ✅ User exists in database (`lisa.prog@mocku.test`)
- ✅ Password hash validates correctly when tested directly
- ✅ Account status is `active`
- ✅ Email is verified
- ✅ No account lock (login_attempts=0, locked_until=NULL)

**But login through API returns**: `401 Invalid email or password`

### **Evidence**

**Database Verification:**
```
Email: lisa.prog@mocku.test
Account Status: active
Email Verified: 1
Password verify result: True (InstitutionAdmin123! matches hash)
Role: program_admin
```

**API Login Test:**
```bash
curl -X POST http://localhost:3002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"lisa.prog@mocku.test","password":"InstitutionAdmin123!"}'

Response: {"error":"Invalid email or password","success":false}
```

**Server Logs Show:**
```
src.services.login_service - ERROR - Login failed for lisa.prog@mocku.test: 
(sqlite3.OperationalError) attempt to write a readonly database
```

### **Root Cause Analysis**

**Initial Hypothesis (INCORRECT)**: Readonly database permissions
- Checked file permissions: `-rw-r--r--` (correct)
- Changed to 664: Still fails
- **Conclusion**: Not a file permission issue

**Current Hypothesis**: Database connection issue
- E2E server may be connecting to wrong database
- Or database handle is readonly mode
- Or WAL mode issue with SQLite

### **What's Working**

- ✅ Site admin login works
- ✅ Institution admin login works
- ✅ Unit tests: 1,578 passing
- ✅ Integration tests: 177 passing (when run without E2E server)
- ✅ Complexity: Passing
- ✅ Smoke tests: Passing (3 tests)

### **What's Failing**

- ❌ E2E tests: Program admin login → 401 Unauthorized
- ❌ Reason: "attempt to write a readonly database" when trying to update last_login_at

### **Next Steps to Investigate**

1. **Check DATABASE_URL in E2E server environment**
   - Is it using the correct database file?
   - Is there a path mismatch?

2. **Check SQLAlchemy connection mode**
   - Is the connection opened in readonly mode?
   - Check SQLiteService initialization

3. **Check if WAL journal files are causing issues**
   - course_records_e2e.db-shm
   - course_records_e2e.db-wal

4. **Verify E2E conftest setup_worker_environment**
   - Line 126: `env["DATABASE_URL"] = f"sqlite:///{worker_db}"`
   - Should it be absolute path?

### **Workaround Options**

1. Skip the last_login_at update in E2E environment
2. Make login service handle readonly databases gracefully
3. Fix the database connection initialization

### **Related Files**

- `tests/e2e/conftest.py` - E2E environment setup
- `src/services/login_service.py` - Login logic
- `src/database/database_sqlite.py` - Database operations
- `src/database/database_sql.py` - SQLite service initialization

### **Current Status**

- All non-E2E checks: PASSING
- E2E tests: BLOCKED on readonly database issue
- CI: Likely has same issue

**Recommendation**: Investigate database connection initialization in E2E environment.

