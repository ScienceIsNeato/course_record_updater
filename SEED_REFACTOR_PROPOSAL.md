# Seed Data Refactoring Proposal

## Problem Statement

We currently maintain two parallel data creation paths:

1. **`scripts/seed_db.py`**: ~800 lines of Python creating test data programmatically
2. **CSV Import Adapter**: Parses CSV files and imports via API

This violates DRY and creates maintenance burden:
- Changes to data model require updating both paths
- Test data can drift between the two approaches
- Seed script bypasses the import validation/business logic
- Twice the code to maintain for the same outcome

## Proposed Solution

**Make `seed_db.py` a thin wrapper that:**

1. Creates minimal bootstrap data (~10 lines):
   - 1 site admin user
   - 1 test institution
   - 1 institution admin user

2. Hits the `/api/import` endpoint with a test CSV file
3. The CSV file becomes the canonical test data source

## Benefits

✅ **Single Source of Truth**: One CSV file for all test data
✅ **Tests the Real Path**: Seeds go through actual import logic
✅ **Easier Maintenance**: Update one CSV, not 800 lines of Python  
✅ **Validation Coverage**: Import validation applies to seed data
✅ **Consistency**: E2E, integration, and manual testing use same data
✅ **Simpler**: ~50 lines of wrapper vs 800 lines of data creation

## Implementation Plan

### Phase 1: Create Canonical Test CSV
```
test_data/seed_data.csv
- 3 institutions (CEI, RCC, PTU)
- 8 programs (CS, EE, Liberal Arts, etc.)
- 15 courses with proper program linkage
- 10 users (admins, program admins, instructors)
- 5 terms
- 15 sections with enrollments
- 35 course outcomes
```

### Phase 2: Refactor seed_db.py
```python
class DatabaseSeeder:
    def seed(self):
        # Step 1: Bootstrap (direct DB)
        self.create_site_admin()
        self.create_test_institution()
        self.create_institution_admin()
        
        # Step 2: Import via API (uses real import path)
        self.import_csv_data("test_data/seed_data.csv")
        
        # Step 3: Minimal post-import cleanup
        self.create_invitations()  # If needed
```

### Phase 3: Validate
- Run E2E tests
- Verify all 40 tests still pass
- Confirm dashboard displays correctly

## Current Status

- **E2E DB Verified**: Courses DO have program_ids linked correctly
- **Dashboard Bug**: May be JavaScript display issue, not data issue
- **This Refactor**: Should happen AFTER fixing current dashboard bug

## Migration Strategy

1. Keep current seed_db.py working
2. Create new `seed_db_v2.py` with thin wrapper approach
3. Run both in parallel, verify identical results
4. Switch E2E tests to v2
5. Remove old seed_db.py once validated

## Estimated Effort

- Create seed CSV: 1-2 hours
- Refactor seed_db.py: 2-3 hours
- Testing/validation: 1-2 hours
- **Total**: 4-7 hours (vs maintaining 800 lines forever)

## Decision

- [ ] Approve refactor after dashboard bug fix
- [ ] Defer until later milestone  
- [ ] Reject (explain why maintaining two paths is better)

