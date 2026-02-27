# CEI Import Adapter Design Document

**Objective:** Import CEI's 2024FAResults.xlsx file into our database with full audit trail and conflict resolution

**Status:** Updated after architectural assessment - Current system CAN be extended to support CEI requirements

---

## Executive Summary: Architectural Assessment

**Decision: KEEP and EXTEND Current System** ✅

After analyzing the current wireframe system against CEI's enterprise requirements, the existing architecture provides a solid foundation that can be evolved rather than rebuilt from scratch.

**Current System Strengths:**

- ✅ Adapter pattern perfectly suited for CEI data import
- ✅ Database service abstraction allows data model evolution
- ✅ Flask foundation can scale with proper restructuring
- ✅ Firestore supports complex relationships needed for CEI

**Required Extensions (Not Replacements):**

- 🔄 **Data Model Evolution**: Expand from flat course records to relational entities
- 🔄 **Authentication Layer**: Add user management and role-based access
- 🔄 **API Restructuring**: Transform single-page app to proper REST API
- 🔄 **UI Transformation**: Evolve form-based UI to dashboard system

**Timeline Impact:** Evolutionary approach saves 4-6 weeks vs. complete rebuild

---

## 0. Current System Integration Strategy

### Leveraging Existing Architecture

**Current Database Service (`database_service.py`)**

- ✅ **Keep**: Abstraction pattern allows easy data model expansion
- 🔄 **Extend**: Add new entity collections (users, course_sections, course_outcomes, terms)
- 🔄 **Enhance**: Add relationship management functions

**Current Adapter Pattern (`adapters/`)**

- ✅ **Keep**: `BaseAdapter` and `FileAdapterDispatcher` are exactly what CEI needs
- 🔄 **Extend**: Add `CEIExcelImportAdapter` using existing pattern
- ✅ **Reuse**: Current validation and error handling framework

**Current Flask API (`app.py`)**

- 🔄 **Restructure**: Transform from single-page to proper REST endpoints
- ✅ **Keep**: Error handling, flash messages, and response patterns
- 🔄 **Extend**: Add authentication middleware and role-based routing

**Current Data Model Evolution Path**

```python
# Current: Flat course record
course = {
    'course_number': 'ACC-201',
    'course_title': 'Accounting Principles',
    'instructor_name': 'John Smith',
    'term': '2024 Fall',
    # ... grade fields
}

# Target: Relational entities
course = {
    'course_id': 'uuid',
    'course_number': 'ACC-201',
    'course_title': 'Accounting Principles'
}

course_section = {
    'section_id': 'uuid',
    'course_id': 'uuid',  # FK to course
    'instructor_id': 'uuid',  # FK to user
    'term_id': 'uuid',  # FK to term
    'section_number': '001',
    'enrollment': 25
}

course_outcome = {
    'outcome_id': 'uuid',
    'course_id': 'uuid',  # FK to course
    'clo_number': '1',
    'description': 'Students will...',
    'assessment_data': {...}
}
```

**Migration Strategy**

1. **Phase 1**: Expand data model while maintaining backward compatibility
2. **Phase 2**: Build CEI import adapter using existing adapter pattern
3. **Phase 3**: Add authentication and role-based UI components
4. **Phase 4**: Transform single-page UI to dashboard system

---

## 1. Research Phase: Excel Document Analysis

### Current Understanding (from SPREADSHEET_ANALYSIS.md)

- **File:** `2024FAresults.xlsx`
- **Main Sheet:** `qry_2024FA_cllos_informer` (1,543 rows × 18 columns)
- **Data Scale:** 173 courses, 312 course-instructor combinations, 145 faculty, 1,543 CLO records

### Research Tasks Needed

- [ ] **Field Mapping Analysis:** Map each Excel column to our data model entities
- [ ] **Data Quality Assessment:** Identify missing data, inconsistencies, or formatting issues
- [ ] **Relationship Extraction:** Understand how courses → sections → instructors → CLOs are linked
- [ ] **Duplicate Detection:** Identify potential duplicate records or data conflicts
- [ ] **Data Validation Rules:** Define what constitutes valid vs. invalid data

### Expected Data Model Mapping

```
Excel → Our Data Model
├── course → Course (platonic form)
├── combo → CourseSection (course + instructor + term)
├── Faculty Name → User (instructor)
├── Term → Academic term structure
├── cllo_text → CourseOutcome (CLO)
├── Enrollment data → CourseSection fields
└── Narrative fields → CourseOutcome fields
```

---

## 2. Architecture Design

### Core Components

#### 2.1 Base Import Adapter

```python
class BaseImportAdapter:
    """Abstract base class for all import adapters"""

    def validate_file(self, file_path: str) -> ValidationResult
    def extract_data(self, file_path: str) -> RawData
    def transform_data(self, raw_data: RawData) -> TransformedData
    def load_data(self, transformed_data: TransformedData) -> ImportResult
    def create_audit_log(self, operation: str, result: ImportResult) -> AuditLogEntry
```

#### 2.2 CEI-Specific Adapter

```python
class CEIExcelImportAdapter(BaseImportAdapter):
    """CEI-specific implementation for 2024FAresults.xlsx format"""

    def parse_excel_sheet(self, file_path: str) -> DataFrame
    def extract_courses(self, df: DataFrame) -> List[Course]
    def extract_course_sections(self, df: DataFrame) -> List[CourseSection]
    def extract_instructors(self, df: DataFrame) -> List[User]
    def extract_clos(self, df: DataFrame) -> List[CourseOutcome]
    def handle_conflicts(self, conflicts: List[DataConflict]) -> ConflictResolution
```

#### 2.3 Conflict Resolution Engine

```python
class ConflictResolutionEngine:
    """Handle data conflicts during import"""

    STRATEGIES = ['use_mine', 'use_theirs', 'merge', 'manual_review']

    def detect_conflicts(self, new_data, existing_data) -> List[DataConflict]
    def resolve_conflict(self, conflict: DataConflict, strategy: str) -> Resolution
    def create_conflict_report(self, conflicts: List[DataConflict]) -> ConflictReport
```

### API Endpoint Design

```
POST /api/import/cei-excel
Content-Type: multipart/form-data

Parameters:
- file: Excel file upload
- conflict_strategy: 'use_mine' | 'use_theirs' | 'merge' | 'manual_review'
- import_source: 'manual' | 'scripted'
- environment: 'dev' | 'test' | 'stage' | 'prod'

Response:
{
  "import_id": "uuid",
  "status": "success|partial|failed",
  "records_processed": 1543,
  "records_created": 1200,
  "records_updated": 300,
  "records_skipped": 43,
  "conflicts_detected": 15,
  "audit_log_id": "uuid",
  "execution_time": "45.2s"
}
```

---

## 3. Environment Separation Strategy

### Environment Configuration

```yaml
environments:
  dev:
    database: "firestore-dev"
    import_endpoint: "https://dev-cei-system.app/api/import"
    audit_retention: "30 days"

  test:
    database: "firestore-test"
    import_endpoint: "https://test-cei-system.app/api/import"
    audit_retention: "90 days"

  stage:
    database: "firestore-stage"
    import_endpoint: "https://stage-cei-system.app/api/import"
    audit_retention: "1 year"

  prod:
    database: "firestore-prod"
    import_endpoint: "https://cei-system.app/api/import"
    audit_retention: "7 years"
```

### Environment-Specific Considerations

- **Dev:** Fast iteration, frequent data resets, minimal validation
- **Test:** Automated testing, consistent test data, full validation
- **Stage:** Production-like data, stakeholder demos, performance testing
- **Prod:** Real CEI data, full audit trail, maximum validation

---

## 4. Multiple Import Handling

### Import Strategies

#### 4.1 First Import (Clean Database)

```python
def handle_first_import(self, data: TransformedData) -> ImportResult:
    """Handle initial import to empty database"""
    # No conflicts possible, create all records
    # Establish baseline audit trail
    # Set all records as "imported" source
```

#### 4.2 Subsequent Imports (Conflict Detection)

```python
def handle_subsequent_import(self, data: TransformedData) -> ImportResult:
    """Handle imports when data already exists"""

    conflicts = self.detect_conflicts(data, existing_data)

    for conflict in conflicts:
        resolution = self.resolve_conflict(conflict, self.conflict_strategy)
        self.apply_resolution(resolution)
        self.log_conflict_resolution(conflict, resolution)
```

### Conflict Resolution Strategies

#### 4.3 "Use Mine" Strategy

- Keep existing database data
- Log attempted changes as conflicts
- Useful when database has been manually updated

#### 4.4 "Use Theirs" Strategy

- Overwrite database with Excel data
- Log previous values as audit trail
- Useful when Excel is authoritative source

#### 4.5 "Merge" Strategy

- Combine data intelligently (e.g., newer timestamps win)
- Complex logic for different field types
- Requires sophisticated conflict resolution rules

#### 4.6 "Manual Review" Strategy

- Flag conflicts for human review
- Create conflict resolution queue
- Allow administrators to decide case-by-case

---

## 5. Audit Log Design

### Audit Log Schema

```python
class AuditLogEntry:
    audit_id: str          # UUID
    timestamp: datetime    # When operation occurred
    operation_type: str    # 'import', 'create', 'update', 'delete', 'conflict_resolution'
    entity_type: str       # 'course', 'course_section', 'user', 'course_outcome'
    entity_id: str         # ID of affected entity
    source_type: str       # 'manual', 'scripted', 'import_adapter'
    source_user: str       # User ID (null for scripted)
    source_system: str     # 'cei_excel_import', 'manual_entry', 'api'

    # Data changes
    old_values: dict       # Previous field values (null for creates)
    new_values: dict       # New field values (null for deletes)

    # Import-specific fields
    import_batch_id: str   # Group related import operations
    conflict_resolution: str  # How conflicts were handled
    validation_errors: list   # Any validation issues encountered

    # Environment tracking
    environment: str       # 'dev', 'test', 'stage', 'prod'
```

### Audit Trail Benefits

- **Conflict Arbitration:** See what changed and when
- **Duplicate Detection:** Identify repeated imports
- **Data Lineage:** Track where each piece of data originated
- **Rollback Capability:** Undo problematic imports
- **Compliance:** Full audit trail for institutional requirements

---

## 6. Data Validation & Quality Assurance

### Validation Layers

#### 6.1 File Validation

- Correct Excel format and structure
- Required sheets and columns present
- Data types match expectations
- No corrupted or unreadable data

#### 6.2 Business Logic Validation

- CLO numbering follows conventions (e.g., "ACC-201.1")
- Enrollment numbers are mathematically consistent
- Pass rates calculate correctly
- Required narrative fields are present

#### 6.3 Referential Integrity Validation

- Course sections reference valid courses
- Instructors are valid users
- CLOs belong to correct courses
- Term/year combinations are valid

#### 6.4 Data Quality Checks

- No duplicate records within import
- Reasonable value ranges (e.g., enrollment 0-1000)
- Text fields contain meaningful content
- Dates are within expected ranges

---

## 7. Implementation Plan

### Phase 1: Research & Analysis

1. **Deep dive into 2024FAresults.xlsx structure**
2. **Create comprehensive field mapping document**
3. **Identify data quality issues and edge cases**
4. **Define validation rules and business logic**

### Phase 2: Environment Setup

1. **Create dev/test/stage/prod environment configurations**
2. **Set up separate Firestore instances**
3. **Configure deployment pipelines**
4. **Establish monitoring and logging**

### Phase 3: Core Adapter Development

1. **Build BaseImportAdapter abstract class**
2. **Implement CEIExcelImportAdapter**
3. **Create comprehensive unit tests**
4. **Add integration tests with sample data**

### Phase 4: Conflict Resolution & Audit

1. **Build ConflictResolutionEngine**
2. **Implement audit logging system**
3. **Create conflict detection algorithms**
4. **Test multiple import scenarios**

### Phase 5: API Integration

1. **Create REST endpoint for import**
2. **Add file upload handling**
3. **Implement response formatting**
4. **Add error handling and logging**

### Phase 6: Testing & Validation

1. **Test with full CEI dataset**
2. **Validate data integrity**
3. **Performance testing with large files**
4. **User acceptance testing with Leslie**

---

## 8. Success Criteria

### Technical Success

- [ ] Import all 1,543 CLO records successfully
- [ ] Maintain referential integrity across all entities
- [ ] Complete audit trail for all operations
- [ ] Handle conflicts gracefully with clear reporting
- [ ] Process import in under 2 minutes

### Business Success

- [ ] Leslie can validate imported data matches Excel
- [ ] All instructor relationships properly established
- [ ] CLO structure matches CEI's current system
- [ ] Export back to Access format maintains fidelity
- [ ] Ready for instructor pilot testing

### Quality Assurance

- [ ] 100% unit test coverage for adapter logic
- [ ] Integration tests for all conflict scenarios
- [ ] Performance benchmarks established
- [ ] Error handling covers all edge cases
- [ ] Documentation complete for maintenance

---

## 9. Risks & Mitigation

### Data Risks

- **Risk:** Data corruption during import
- **Mitigation:** Comprehensive validation, rollback capability, staging environment testing

### Technical Risks

- **Risk:** Performance issues with large datasets
- **Mitigation:** Streaming processing, batch operations, performance testing

### Business Risks

- **Risk:** Imported data doesn't match CEI expectations
- **Mitigation:** Close collaboration with Leslie, validation reports, sample data testing

### Operational Risks

- **Risk:** Import conflicts cause data inconsistencies
- **Mitigation:** Robust conflict resolution, audit trails, manual review options

This design provides a solid foundation for building a reliable, auditable import system that bridges CEI's existing data into our new platform while maintaining data integrity and providing clear visibility into all operations.
