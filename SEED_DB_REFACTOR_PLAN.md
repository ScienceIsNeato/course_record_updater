# seed_db.py Architectural Refactoring Plan

**Created**: 2026-01-07  
**For**: Dany (execution) / Pacey (steering)  
**Goal**: Salvage current improvements without deep refactoring rabbit hole

---

## Current State Analysis

### File Structure (1,536 lines)
```
scripts/seed_db.py
├── BaselineSeeder (lines 40-608)      # 568 lines - PROBLEM: Hardcoded test data
├── DatabaseSeeder (lines 611-626)     # 15 lines - Compatibility wrapper
└── DemoSeeder (lines 628-1536)        # 908 lines - PROBLEM: Extends BaselineSeeder with more hardcoded demo data
```

### The Problem
**Original Intent**: Lightweight manifest-driven wrapper  
**Current Reality**: 1,536 lines of hardcoded literal strings in class methods

**Hardcoded Data Examples:**
- Institution names: "Mock University", "Riverside Community College", "Pacific Technical University"
- User data: emails, names, roles hardcoded in methods
- Course data: "CSCI-101", "BIOL-101", etc. all inline
- Program definitions: departments, descriptions
- Term structures: dates, names, etc.

**What SHOULD Have Happened:**
- Manifest JSON files contain ALL data
- Seeder classes are THIN wrappers that:
  1. Read manifest
  2. Validate structure
  3. Call database service methods
  4. Log results

---

## Proposed Refactoring

### Phase 1: Class Hierarchy Restructuring (This PR - Minimal Changes)

```
BaselineSeeder (Abstract)          # NEW: Abstract base class with shared utilities
    ├── log()                       # Shared logging
    ├── load_manifest()             # Shared manifest loading
    └── Abstract methods to override

BaselineTestSeeder                 # RENAMED from BaselineSeeder
    ├── Hardcoded test data (3 institutions, programs, terms)
    ├── For E2E/integration tests only
    └── Extends BaselineSeeder

DemoSeeder                         # UPDATED
    ├── Hardcoded demo-specific data
    ├── Extends BaselineTestSeeder (inherits test infrastructure)
    └── Adds demo scenarios on top
```

**Key Changes:**
1. Rename `BaselineSeeder` → `BaselineTestSeeder`
2. Create new abstract `BaselineSeeder` base class
3. Update `DemoSeeder` to extend `BaselineTestSeeder`
4. Add docstrings marking hardcoded data as "TODO: Move to manifest"
5. Update CLI argument parsing to use correct classes

**Benefits:**
- Clear separation of concerns
- Marks technical debt explicitly
- Preserves current functionality
- Sets up clean migration path

### Phase 2: Data Extraction (Future Ticket - NOT This PR)

**Future Work** (don't do now):
1. Extract BaselineTestSeeder data → `tests/fixtures/baseline_test_manifest.json`
2. Extract DemoSeeder data → enhance `demos/full_semester_manifest.json`
3. Convert classes to thin manifest readers
4. Remove all hardcoded literal strings

---

## Implementation Plan (Phase 1 Only)

### Step 1: Create Abstract Base Class
**File**: `scripts/seed_db.py` (top of file, before current BaselineSeeder)

```python
class BaselineSeeder(ABC):
    """
    Abstract base class for database seeding operations.
    
    Provides shared utilities for manifest loading, logging, and database interaction.
    Subclasses implement specific seeding strategies (test vs demo vs production).
    """
    
    def __init__(self):
        self.created = {
            "institutions": [],
            "users": [],
            "programs": [],
            "terms": [],
            "courses": [],
        }
    
    def log(self, message: str):
        """Log with [SEED] prefix"""
        print(f"[SEED] {message}")
    
    def load_manifest(self, manifest_path: Optional[str]) -> Dict[str, Any]:
        """Load and parse manifest JSON file (shared utility)"""
        # Move existing load_demo_manifest logic here
        ...
    
    @abstractmethod
    def seed(self):
        """Implement seeding logic in subclasses"""
        pass
```

### Step 2: Rename BaselineSeeder → BaselineTestSeeder
**Change**: Line 40

```python
class BaselineTestSeeder(BaselineSeeder):
    """
    Seeds baseline test infrastructure for E2E/integration tests.
    
    TODO (Future): Move hardcoded data to tests/fixtures/baseline_test_manifest.json
    This class currently contains hardcoded institution, program, and term data
    that should be externalized to JSON manifests for flexibility.
    """
    
    def __init__(self):
        super().__init__()
    
    def seed_baseline(self, manifest_data=None):
        """Seed minimal baseline data for E2E tests"""
        # Existing implementation stays the same
        ...
```

### Step 3: Update DemoSeeder Inheritance
**Change**: Line 628

```python
class DemoSeeder(BaselineTestSeeder):  # Changed from BaselineSeeder
    """
    Complete seeding for product demonstrations (2025).
    
    TODO (Future): Move demo-specific data to demos/full_semester_manifest.json
    This class extends BaselineTestSeeder and adds demo-specific scenarios,
    users, and CLO workflows. All hardcoded data should eventually be in manifest.
    """
    
    def __init__(self, manifest_path=None):
        super().__init__()
        self.manifest_path = manifest_path
    
    # Existing implementation
    ...
```

### Step 4: Update DatabaseSeeder Wrapper
**Change**: Line 611

```python
class DatabaseSeeder:
    """
    Compatibility wrapper for integration tests.
    Uses BaselineTestSeeder internally.
    """
    
    def __init__(self, verbose=True):
        self.seeder = BaselineTestSeeder()  # Changed from BaselineSeeder
        self.verbose = verbose
```

### Step 5: Update CLI Argument Handler
**Search for**: `--env` argument parsing logic (near bottom of file)

```python
if args.env == "dev":
    seeder = BaselineTestSeeder()  # Changed from BaselineSeeder
    seeder.seed_baseline()
elif args.demo:
    seeder = DemoSeeder(manifest_path=args.manifest)
    seeder.seed_demo()
```

### Step 6: Add Import for ABC
**Top of file** (around line 9):

```python
from abc import ABC, abstractmethod
```

---

## Validation Checklist

After implementation:
- [ ] All existing tests still pass
- [ ] `python scripts/seed_db.py --env dev` works (BaselineTestSeeder)
- [ ] `python scripts/seed_db.py --demo --manifest demos/full_semester_manifest.json` works (DemoSeeder)
- [ ] No functional changes - only architectural restructuring
- [ ] All docstrings include "TODO (Future)" notes for data extraction
- [ ] Clear inheritance hierarchy visible

---

## Out of Scope (Future Ticket)

**DO NOT DO IN THIS PR:**
- Extract data to JSON manifests
- Remove hardcoded strings
- Refactor method signatures
- Change seeding behavior
- Add new manifest fields

**The Goal**: Make architectural bones correct NOW, defer data extraction to future ticket

---

## Key Insights for Dany

1. **Rename carefully**: BaselineSeeder → BaselineTestSeeder affects:
   - DatabaseSeeder class (line ~620)
   - CLI argument parsing (bottom of file)
   - Import statements in tests (potentially)

2. **Inheritance chain**:
   ```
   BaselineSeeder (abstract)
       ↓
   BaselineTestSeeder (concrete - test data)
       ↓
   DemoSeeder (concrete - demo data on top of test data)
   ```

3. **No behavior changes**: This is pure restructuring. If tests break, rollback and investigate.

4. **Mark technical debt**: Every hardcoded data method should have comment:
   ```python
   # TODO (Future): Move to manifest - see SEED_DB_REFACTOR_PLAN.md Phase 2
   ```

5. **Test after each step**: 
   - After renaming, run: `python scripts/seed_db.py --env dev`
   - After DemoSeeder change, run: `python scripts/seed_db.py --demo --manifest demos/full_semester_manifest.json`

---

## Estimated Effort

**Phase 1 (This PR)**: ~30 minutes
- Mostly find/replace with careful validation
- 6 small changes across 1 file
- Risk: Low (no logic changes)

**Phase 2 (Future)**: ~4-6 hours
- Data extraction to JSON
- Manifest schema design
- Comprehensive testing
- Risk: Medium (behavior changes)

---

## Success Criteria

✅ Class hierarchy clearly shows intent  
✅ Abstract base separates concerns  
✅ Technical debt explicitly marked  
✅ No functional regressions  
✅ All tests still pass  
✅ Ready for future data extraction  

---

## Questions for Pacey

1. Should the abstract `BaselineSeeder` have any concrete methods besides `log()` and `load_manifest()`?
2. Do you want `seed()` as the abstract method name, or keep `seed_baseline()` / `seed_demo()`?
3. Any other utility methods that should be in the abstract base?

---

**Ready for Dany to execute**: Follow steps 1-6 sequentially, test after each change, commit when all passing.

