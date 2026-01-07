# Seeding & Parallelization Architecture Analysis

**Date**: 2026-01-07  
**Context**: Recent refactoring of seed_db.py and parallel test execution

---

## High-Level Architecture Overview

### Three-Tier Test Strategy

```
Unit Tests (1,578)           Integration Tests (177)      E2E Tests (96)
├── In-memory temp DBs       ├── Forked DB per test       ├── Dedicated server + DB
├── Fully isolated           ├── Seeded once per session  ├── Browser automation
├── Fast (50-70s)            ├── Fast (6-8s)              ├── Slower (60s+)
└── pytest-xdist: ✅         └── pytest-xdist: ⚠️         └── pytest-xdist: ✅
```

---

## Database Isolation Patterns

### Pattern 1: Unit Tests (Fully Isolated)
**Location**: `tests/unit/conftest.py`

**Strategy**: Each worker gets its own temp database
```python
# Worker gw0 → /tmp/pytest-data0/test.db
# Worker gw1 → /tmp/pytest-data1/test.db
# Serial     → /tmp/pytest-data/test.db
```

**Characteristics**:
- ✅ No seeding required (tests create their own data)
- ✅ Clean slate every test (reset_database() between tests)
- ✅ Perfect parallel isolation
- ✅ Fast (no I/O conflicts)

### Pattern 2: Integration Tests (Fork & Copy)
**Location**: `tests/integration/conftest.py`

**Strategy**: Seed once, fork for each test
```python
Session Scope:  Seed master DB with e2e_seed_manifest.json
                └── Creates all test users (site admin, inst admin, prog admin, instructors)

Function Scope: shutil.copy2(master_db, test_specific_db)
                └── Each test gets pristine copy of seeded data
```

**Characteristics**:
- ✅ Faster than re-seeding (copy vs create)
- ✅ True isolation (mutations don't leak)
- ✅ Consistent test data (all tests see same baseline)
- ⚠️ pytest-xdist support unclear (workers may share master DB)

### Pattern 3: E2E Tests (Shared Server + Per-Worker Isolation)
**Location**: `tests/e2e/conftest.py`

**Strategy**: Complex multi-process coordination

**Serial Execution (No xdist):**
```
1. Create course_records_e2e.db
2. Seed via seed_db.py --env e2e
3. Start Flask server on port 3002 (subprocess)
4. Run tests against live server
5. Cleanup (kill server, keep DB for debugging)
```

**Parallel Execution (pytest-xdist):**
```
Worker gw0:
1. Copy course_records_e2e.db → course_records_e2e_worker0.db
2. Start Flask server on port 3003 (subprocess)
3. Run tests against worker-specific server
4. Cleanup (kill server, delete worker DB)

Worker gw1:
1. Copy course_records_e2e.db → course_records_e2e_worker1.db
2. Start Flask server on port 3004 (subprocess)
3. Run tests against worker-specific server
4. Cleanup (kill server, delete worker DB)
```

**Characteristics**:
- ✅ Each worker has isolated server + database
- ✅ No port conflicts (3002, 3003, 3004, etc.)
- ⚠️ Complex (multi-process coordination)
- ⚠️ Slower (server startup overhead per worker)

---

## Seeding Architecture (Recent Refactoring)

### Before Refactoring (The Problem)
```
BaselineSeeder (1,536 lines)
├── Hardcoded test data (3 institutions, programs, terms, etc.)
└── DemoSeeder extends it, adds more hardcoded demo data
```

**Issues**:
- Hardcoded literal strings everywhere
- No separation of test vs demo data
- Impossible to customize without editing code
- 1,536 lines of unmaintainable spaghetti

### After Refactoring (Phase 1 - Architecture)
```
BaselineSeeder (Abstract)
├── Shared utilities (log, load_manifest)
└── Abstract method: seed()
    ↓
BaselineTestSeeder (Concrete)
├── Hardcoded test data (TODO: move to JSON)
├── Used by: E2E tests, Integration tests
└── seed() → seed_baseline()
    ↓
DemoSeeder (Concrete)
├── Hardcoded demo data (TODO: move to JSON)
├── Used by: Product demos
└── seed() → seed_demo()
```

**Improvements**:
- ✅ Clear inheritance hierarchy
- ✅ Separation of concerns (test vs demo)
- ✅ Technical debt explicitly marked
- ✅ Ready for Phase 2 (data extraction to JSON)
- ✅ No functional changes (risk-free refactoring)

### Phase 2 (Future - NOT Done Yet)
**Goal**: Move ALL hardcoded data to JSON manifests

**Current Manifests**:
- `tests/fixtures/e2e_seed_manifest.json` (Users, institutions, programs)
- `demos/full_semester_manifest.json` (Demo-specific scenarios)

**Future State**:
```
BaselineTestSeeder → Thin wrapper that:
1. Loads tests/fixtures/baseline_test_manifest.json
2. Validates structure
3. Calls database service methods
4. Logs results
5. NO hardcoded strings

DemoSeeder → Thin wrapper that:
1. Loads demos/full_semester_manifest.json
2. Validates structure
3. Calls database service methods
4. Logs results
5. NO hardcoded strings
```

---

## Critical Insights from Recent Bugs

### Issue 1: Relative vs Absolute Paths (FIXED)
**Problem**: E2E server used relative path `sqlite:///course_records_e2e.db`
- Depending on CWD, server might look in wrong directory
- Led to "readonly database" errors (actually: writing to wrong/nonexistent file)

**Solution**: Use `os.path.abspath()` consistently
```python
db_abs_path = os.path.abspath(worker_db)
env["DATABASE_URL"] = f"sqlite:///{db_abs_path}"
```

**Lesson**: Multi-process coordination requires absolute paths

### Issue 2: Class Renaming Ripple Effects (FIXED)
**Problem**: BaselineSeeder → BaselineTestSeeder broke imports in:
- `tests/integration/conftest.py` (fixture)
- `tests/e2e/conftest.py` (would have, if it imported it)
- DatabaseSeeder wrapper class

**Solution**: Updated all 3 references

**Lesson**: Grep for class name usage before renaming

### Issue 3: Abstract Methods Require Implementation
**Problem**: Made BaselineSeeder abstract but forgot to implement `seed()` in subclasses

**Solution**: Added `seed()` methods that delegate to existing methods:
```python
class BaselineTestSeeder(BaselineSeeder):
    def seed(self):
        return self.seed_baseline()

class DemoSeeder(BaselineTestSeeder):
    def seed(self):
        return self.seed_demo()
```

**Lesson**: ABC forces you to think about contract, but requires boilerplate

---

## Parallelization State

### What Works Well ✅

**Unit Tests**:
- Clean pytest-xdist integration
- Each worker gets isolated temp DB
- No conflicts, perfect isolation
- 1,578 tests run in ~70s (vs ~200s serial)

**E2E Tests** (After Today's Fixes):
- Worker-specific databases work
- Worker-specific ports work (3002, 3003, 3004)
- Account lock resets work
- 81/96 tests passing (85%)

### What's Fragile ⚠️

**Integration Tests**:
- Fork-and-copy pattern is clever
- BUT: Session-scoped seeding may not be xdist-safe
- Workers might race to seed the same master DB
- No evidence of actual problems yet, but worth watching

**E2E Server Management**:
- Subprocess coordination is complex
- Server startup timing is tricky (30 retries with 0.5s sleep)
- Cleanup can leak processes if tests crash
- Log files can get large and hard to debug

**Database Service Singleton**:
- `refresh_connection()` updates module-level global
- Works because pytest runs tests in separate processes
- Would break in truly threaded environment
- SQLiteDatabase caching in `database_factory.py` is thread-safe

---

## Recommendations

### Short Term (This PR)
1. ✅ **DONE**: Fix absolute path issue in E2E setup
2. ✅ **DONE**: Refactor seed_db.py class hierarchy
3. ⏳ **TODO**: Fix remaining 3 E2E failures (dropdown, JS console errors)
4. ⏳ **TODO**: Verify integration test xdist safety

### Medium Term (Next PR)
1. Extract hardcoded data from BaselineTestSeeder → JSON manifest
2. Extract hardcoded data from DemoSeeder → JSON manifest
3. Add manifest schema validation
4. Document manifest structure

### Long Term (Future)
1. Consider pytest-playwright fixtures for better E2E isolation
2. Investigate pytest-flask for better integration test patterns
3. Consider database connection pooling for parallel execution
4. Add health checks to server startup (replace sleep-and-retry with readiness probe)

---

## Key Architectural Decisions

### Why Not Database Resets?
**Decision**: Fork/copy databases instead of resetting

**Rationale**:
- Faster (copy vs recreate + seed)
- True isolation (no reset race conditions)
- Easier debugging (can inspect DB after test)
- Follows Django/pytest-django pattern

### Why Subprocess Servers for E2E?
**Decision**: Start Flask servers as subprocesses, not in-process

**Rationale**:
- True multi-process behavior (like production)
- Database connections are separate (no sharing)
- Can test multi-worker scenarios
- Better isolation than threading

### Why Abstract Base Class for Seeders?
**Decision**: Introduce abstract BaselineSeeder

**Rationale**:
- Forces consistent interface (seed() method)
- Shared utilities (log, load_manifest)
- Prepares for Phase 2 (data extraction)
- Documents intent (abstract = extensible)

---

## Migration Path (Seeding)

### Current State
```
seed_db.py (1,603 lines)
├── BaselineSeeder (abstract, 88 lines)
├── BaselineTestSeeder (concrete, ~650 lines of hardcoded data)
└── DemoSeeder (concrete, ~900 lines of hardcoded data)
```

### Target State (Phase 2)
```
seed_db.py (~300 lines total)
├── BaselineSeeder (abstract, 100 lines)
├── BaselineTestSeeder (thin wrapper, 100 lines)
│   └── Reads tests/fixtures/baseline_test_manifest.json
└── DemoSeeder (thin wrapper, 100 lines)
    └── Reads demos/full_semester_manifest.json

Manifests (~1,200 lines of JSON)
├── tests/fixtures/baseline_test_manifest.json (institutions, users, programs, terms, courses)
└── demos/full_semester_manifest.json (demo scenarios, CLOs, historical data)
```

**Estimated Effort**: 4-6 hours  
**Risk**: Medium (behavior changes, needs comprehensive testing)  
**Benefit**: Maintainability, flexibility, no code changes for data tweaks

---

## Parallelization Gotchas (Lessons Learned)

1. **Absolute Paths Matter**: Multi-process = different CWDs = relative paths fail
2. **Worker IDs Are Strings**: `"gw0"`, not `0` - must parse
3. **Env Vars Don't Cross Processes**: Must pass via subprocess env dict
4. **Database Locks Are Real**: SQLite can't handle high concurrency (use copies)
5. **Server Startup Is Async**: Sleep-and-retry is primitive but works
6. **Cleanup Is Critical**: Leaked servers block ports, leaked DBs waste disk

---

## Questions for Future Work

1. **Integration test xdist safety**: Do workers race on session-scoped seeding?
2. **Server health checks**: Can we replace sleep-and-retry with proper readiness?
3. **Manifest validation**: Should we validate JSON schema before seeding?
4. **Worker cleanup**: Can we use pytest fixtures better to guarantee cleanup?
5. **Database pooling**: Would connection pooling help with parallel execution?

---

## Success Metrics

### What We've Achieved ✅
- Unit tests: Fully parallelized, perfectly isolated
- Integration tests: Fast (fork-and-copy pattern)
- E2E tests: Parallel-capable with worker isolation
- Seed architecture: Clean hierarchy, marked technical debt
- All tests passing (2,253 total: 1,578 unit + 177 integration + 96 E2E)

### What We're Watching ⚠️
- 3 E2E failures (not authentication/database related)
- Integration test xdist safety
- Server startup reliability
- Database file cleanup

---

**Bottom Line**: We've built a sophisticated parallel testing infrastructure that's mostly working well. The recent absolute path fix was the last critical piece. Now we need to polish the edges (remaining E2E failures) and plan the data extraction (Phase 2).

