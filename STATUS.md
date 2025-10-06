# Status: Generic CSV Adapter - Ready for Export Implementation

## Progress: 2/8 Core Steps Complete (25%)

### Completed ✅
- [x] **Step 1**: Schema design (ZIP of normalized CSVs, security decisions)
- [x] **Step 2**: Adapter scaffold (auto-discovery, metadata, validation)

### Current: Step 3 - Export Implementation (TDD) 🏗️

---

## Testing Progression Strategy

### Phase 1: Unit Tests (First)
**Purpose**: Test individual methods in isolation with mocked dependencies

**Export Tests** (`tests/unit/test_generic_csv_adapter.py`):
- `test_export_empty_data` - Handles empty datasets gracefully
- `test_export_single_institution` - Basic export with minimal data
- `test_export_with_relationships` - Foreign keys, many-to-many associations
- `test_export_excludes_sensitive_fields` - password_hash, tokens excluded
- `test_export_serializes_json_fields` - extras, grade_distribution, assessment_data
- `test_export_creates_valid_zip` - ZIP structure correct
- `test_export_manifest_accurate` - Entity counts match

**Import Tests** (after export works):
- `test_import_validates_manifest`
- `test_import_respects_order` - Foreign key dependencies
- `test_import_regenerates_tokens`
- `test_import_sets_users_pending`
- `test_import_deserializes_json`

### Phase 2: Integration Tests (Second)
**Purpose**: Test full workflows with real database interactions

**Tests** (`tests/integration/test_generic_csv_adapter.py`):
- `test_full_export_import_cycle` - Export → Import with real DB
- `test_adapter_registry_discovery` - Auto-registration works
- `test_export_import_preserves_relationships` - Foreign keys maintained
- `test_import_handles_missing_foreign_keys` - Graceful error handling

### Phase 3: Smoke Tests (If Prudent)
**Purpose**: Quick sanity checks for critical paths

**Evaluate**:
- Adapter loads without errors
- File validation catches invalid ZIPs
- Export doesn't crash with realistic data
- Import doesn't crash with valid ZIP

### Phase 4: E2E Tests (Final)
**Purpose**: Full system test through UI (TC-IE-104)

**Test** (`tests/e2e/test_import_export.py`):
- `test_tc_ie_104_roundtrip_validation` - Complete bidirectional flow:
  1. Seed DB with data
  2. Export via UI (Generic CSV adapter)
  3. Clear DB
  4. Import exported file via UI
  5. Export again
  6. Compare files (data integrity)

---

## Detailed TODO List

### Unit Testing & Implementation
- [ ] **3a**: Write export unit tests (TDD)
- [ ] **3b**: Implement CSV export_data() method
- [ ] **4**: Create seed data script
- [ ] **5**: Manual export verification
- [ ] **6a**: Write import unit tests (TDD)
- [ ] **6b**: Implement CSV parse_file() method

### Integration & Smoke
- [ ] **7a**: Add integration tests (full workflow)
- [ ] **7b**: Evaluate smoke tests (if prudent)

### Validation & E2E
- [ ] **8a**: Manual roundtrip validation
- [ ] **8b**: Implement TC-IE-104 E2E test

---

## Current Focus: Step 3a - Export Unit Tests

**Next Action**: Write comprehensive unit tests for export functionality (TDD approach)

**File**: `tests/unit/test_generic_csv_adapter.py` (new file)

**Test Coverage**:
- Basic functionality (empty data, single entity)
- Relationships (foreign keys, associations)
- Security (sensitive field exclusion)
- Data serialization (JSON fields)
- File structure (ZIP, manifest, CSVs)
- Error handling (invalid data, missing fields)

**Let's go! 🚀**
