# Status: Generic CSV Adapter - Schema Complete, Moving to Scaffold

## Step 1: ✅ COMPLETE - Schema Design

### Final Design Decisions:

**1. Format**: ZIP of 12 normalized CSV files + manifest.json ✅

**2. Security Approach**: Always Exclude Sensitive Data ✅
- **Excluded**: `password_hash`, all active tokens
- **Import Behavior**: Users created as "pending", must complete registration
- **Trade-off**: Security over immediate usability
- **Rationale**: Prevents password exposure, token reuse attacks

**3. Extras Handling**: Serialize as JSON ✅
- Export: PickleType → JSON string
- Import: JSON string → dict
- Empty: `{}`

### Updated Spec: `CSV_FORMAT_SPEC.md`

**Changes**:
- Removed sensitive fields from `users.csv` (password_hash, tokens)
- Removed token from `user_invitations.csv` (regenerated on import)
- Added "Security & Privacy" section
- Documented import behavior for users (pending status, no immediate login)
- Added extras serialization notes

---

## Step 2: IN PROGRESS - Adapter Scaffold

### Next Actions:
1. Create `adapters/generic_csv_adapter.py`
2. Extend `FileBaseAdapter` 
3. Implement adapter metadata
4. Register with adapter registry
5. Add basic export/import method stubs

### Structure:
```python
class GenericCSVAdapter(FileBaseAdapter):
    """Generic CSV adapter - ZIP of normalized CSVs"""
    
    def get_adapter_info(self):
        return {
            "id": "generic_csv_v1",
            "name": "Generic CSV Format",
            "supported_formats": [".zip"],
            ...
        }
    
    def export_data(self, data_dict, output_path):
        # Step 3: Implementation
        pass
    
    def import_data(self, file_path):
        # Step 6: Implementation
        pass
```

---

## Progress Tracker

- [x] **Step 1**: Schema design
  - [x] Database → CSV mapping
  - [x] Security decisions
  - [x] Extras handling
  - [x] Documentation
- [ ] **Step 2**: Adapter scaffold
- [ ] **Step 3**: Export implementation (TDD)
- [ ] **Step 4**: Seed data creation
- [ ] **Step 5**: Manual export test
- [ ] **Step 6**: Import implementation (TDD)
- [ ] **Step 7**: Roundtrip validation
- [ ] **Step 8**: E2E test (TC-IE-104)

**Key Learning**: Caught PII issue early (password_hash), chose secure-by-default approach. ✅
