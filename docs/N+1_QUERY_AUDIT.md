# N+1 Query Performance Audit

**Date**: 2026-01-17  
**Scope**: Full codebase sweep for database query performance issues

## Critical Path (High Traffic) - FIXED ✅

### 1. Audit CLO Page - `/api/outcomes/audit` ✅ FIXED

**Location**: `src/services/clo_workflow_service.py::get_clos_by_status()`  
**Impact**: HIGH - Loads on every audit page visit  
**Frequency**: Every page load for program/institution admins

**Problem**:

- For 100 outcomes, made 900+ queries:
  - 1 initial query
  - Per outcome (×100): template, course, programs, instructor, section, offering, term, history

**Fix Applied**:

- Added eager loading with `joinedload()` and `selectinload()` in `database_sqlite.py`
- Updated `to_dict()` methods to include eager-loaded data
- Updated service layer to use eager-loaded data instead of re-querying
- Reduced to 1-3 queries total

**Performance**:

- Before: 10-40 seconds
- After: <1 second
- Improvement: 10-40x faster

### 2. Frontend Stats Requests ✅ FIXED

**Location**: `static/audit_clo.js::updateStats()`  
**Impact**: HIGH - Every audit page load  
**Frequency**: Every page load

**Problem**:

- Made 7 separate API requests just to get status counts
- Each request fetched full outcome data just to count records

**Fix Applied**:

- Added `include_stats=true` parameter to `/api/outcomes/audit`
- Backend calculates stats from already-fetched data
- Frontend makes 1 request instead of 7

**Performance**:

- Before: 7 HTTP requests
- After: 1 HTTP request (included with main data fetch)

## Medium Priority (Occasional Use)

### 3. Submit Course for Approval - N+1 Issue ⚠️ NOT FIXED YET

**Location**: `src/services/clo_workflow_service.py:786-790`  
**Impact**: MEDIUM - Used when instructors submit courses  
**Frequency**: Few times per semester per course

**Problem**:

```python
section_outcomes = []
for section in sections:
    sect_id = section.get("section_id")
    if sect_id:
        outcomes = db.get_section_outcomes_by_section(sect_id)  # N+1 query!
        section_outcomes.extend(outcomes)
```

**Recommended Fix**:

- Add `get_section_outcomes_by_course(course_id)` method to database layer
- Single query with JOIN instead of loop

**Estimated Impact**: 5-10 sections per course × 40ms = 200-400ms → <50ms

### 4. Bulk Email Instructor Lookup - N+1 Issue ⚠️ NOT FIXED YET

**Location**: `src/services/bulk_email_service.py:60-64`  
**Impact**: MEDIUM - Used when sending bulk reminder emails  
**Frequency**: Occasionally (bulk operations)

**Problem**:

```python
recipients = []
for instructor_id in instructor_ids:
    user = db.execute(
        select(User).where(User.id == instructor_id)
    ).scalar_one_or_none()  # N+1 query!
```

**Recommended Fix**:

- Fetch all users in single query: `select(User).where(User.id.in_(instructor_ids))`
- Build recipient list from results

**Estimated Impact**: 50 instructors × 40ms = 2 seconds → <50ms

## Low Priority (Negligible Impact)

### 5. Dashboard Service - Program Lookups

**Location**: `src/services/dashboard_service.py:190-208`  
**Impact**: LOW - Dashboard data fetched from cache  
**Frequency**: Once per session (cached)

**Problem**: Minor - program lookups in loop, but uses in-memory index

**Fix**: Not needed - already using in-memory program_index, no database queries in loop

## Summary

### Fixed:

- ✅ Audit CLO page (critical path) - 10-40x faster
- ✅ Frontend stats consolidation - 7 requests → 1

### Remaining (Low Priority):

- ⚠️ Submit course for approval (medium impact, infrequent use)
- ⚠️ Bulk email instructor lookup (medium impact, infrequent use)

### Recommendation:

**Ship current fixes immediately** - they solve the critical user-facing performance issue.  
Address remaining N+1 queries in follow-up PR if they become noticeable in production usage.

## Testing Checklist

- [x] Audit page loads in <1 second
- [x] No 500 errors in logs
- [x] All status tabs work correctly
- [ ] Submit course workflow (when testing submission feature)
- [ ] Bulk email reminders (when testing reminder feature)
