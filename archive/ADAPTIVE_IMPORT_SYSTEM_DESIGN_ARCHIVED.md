# Adaptive Import System Design

## Overview

The Course Record Updater uses a flexible, institution-specific adapter system that allows each institution to import data in their unique formats without requiring system-wide changes. This document outlines the architecture, workflow, and implementation details of this adaptive import system.

## Core Philosophy

### Institution-Centric Approach
- **Each institution has unique data formats**: No two institutions structure their data identically
- **One-off custom development**: Adapters are developed on-demand by the system developer
- **Automatic format detection**: The system determines data types from file content, not user selection
- **Scoped adapter access**: Users only see adapters relevant to their institution

### Adapter-Driven Data Detection
- **No manual data type selection**: Users don't choose "courses" vs "students" - the adapter determines this
- **File format flexibility**: Adapters can handle Excel, CSV, JSON, or any structured format
- **Content-based validation**: Each adapter validates file compatibility before processing

## System Architecture

### Adapter Hierarchy

```
BaseAdapter (Abstract)
├── validate_file_compatibility(file) -> bool
├── detect_data_types(file) -> list[str]
├── parse_file(file) -> dict
└── get_adapter_info() -> dict

Institution-Specific Adapters
├── MockUExcelAdapter
│   ├── handles: .xlsx files with MockU's course/faculty structure
│   ├── detects: courses, sections, faculty, assessments
│   └── validates: column headers, data formats
├── PTUCSVAdapter
│   ├── handles: .csv files with PTU's student enrollment format
│   ├── detects: students, enrollments
│   └── validates: required columns, ID formats
└── RCCJSONAdapter
    ├── handles: .json files with RCC's program data
    ├── detects: programs, courses
    └── validates: JSON schema, required fields
```

### User Workflow

1. **File Upload**: User selects any data file
2. **Adapter Selection**: User chooses from institution-scoped adapters
3. **Compatibility Check**: Selected adapter validates file format
4. **Data Detection**: Adapter determines what data types are present
5. **Import Configuration**: User configures conflict resolution, options
6. **Processing**: Adapter parses and imports data
7. **Results**: System reports what was imported and any issues

### Role-Based Adapter Access

```yaml
Site Admin:
  - Access: All adapters across all institutions
  - Use Case: System administration, cross-institution data migration

Institution Admin:
  - Access: All adapters for their institution
  - Use Case: Import various data types for their institution

Program Admin:
  - Access: All adapters for their institution
  - Use Case: Import course/student data for their programs

Instructor:
  - Access: Export only, no import capabilities
  - Message: "Contact your program administrator to request data imports"
```

## Adapter Development Process

### Request Workflow
1. **Institution Request**: Institution admin contacts system developer
2. **Data Analysis**: Developer analyzes institution's data format
3. **Adapter Development**: Custom adapter created for institution
4. **Testing**: Adapter tested with institution's sample data
5. **Deployment**: Adapter deployed and made available to institution users

### Adapter Specifications

#### Required Methods
```python
class BaseAdapter:
    def validate_file_compatibility(self, file_path: str) -> bool:
        """Check if file format matches adapter expectations"""
        pass
    
    def detect_data_types(self, file_path: str) -> List[str]:
        """Determine what types of data are in the file"""
        pass
    
    def get_adapter_info(self) -> Dict[str, Any]:
        """Return adapter metadata for UI display"""
        pass
    
    def parse_file(self, file_path: str, options: Dict) -> ImportResult:
        """Process the file and return structured data"""
        pass
```

#### Adapter Metadata
```python
def get_adapter_info(self) -> Dict[str, Any]:
    return {
        "name": "MockU Excel Format",
        "description": "Imports course, faculty, and assessment data from MockU's Excel exports",
        "supported_formats": [".xlsx", ".xls"],
        "institution_id": "mocku_institution_id",
        "data_types": ["courses", "sections", "faculty", "assessments"],
        "version": "1.2.0",
        "created_by": "System Developer",
        "last_updated": "2024-09-25"
    }
```

## User Interface Design

### Import Panel Components

#### File Upload Section
```html
<div class="file-upload">
    <label>Select Data File:</label>
    <input type="file" accept="*" />
    <small>Format will be detected by selected adapter</small>
</div>
```

#### Adapter Selection
```html
<div class="adapter-selection">
    <label>Import Adapter:</label>
    <select name="import_adapter">
        <!-- Populated based on user's institution scope -->
        <option value="mocku_excel_v1">MockU Excel Format v1.2</option>
        <option value="mocku_csv_v1">MockU CSV Format v1.0</option>
    </select>
    <small>Only adapters for your institution are shown</small>
</div>
```

#### Compatibility Status
```html
<div class="compatibility-check" id="compatibilityStatus">
    <!-- Populated after file upload and adapter selection -->
    <div class="alert alert-success">
        ✅ File compatible with MockU Excel Format
        Detected data types: Courses (45), Faculty (12), Assessments (180)
    </div>
    <!-- OR -->
    <div class="alert alert-danger">
        ❌ File incompatible with MockU Excel Format
        Contact your institution admin to request a custom adapter for this format.
    </div>
</div>
```

### Export Panel Components

#### Output Format Selection
```html
<div class="export-adapter">
    <label>Output Format:</label>
    <select name="export_adapter">
        <!-- Same institution-scoped adapters -->
        <option value="mocku_excel_v1">MockU Excel Format v1.2</option>
        <option value="generic_csv">Generic CSV Format</option>
    </select>
</div>
```

## Error Handling & User Guidance

### Compatibility Errors
- **Primary Message**: "File incompatible with [Adapter Name]"
- **Action Required**: "Contact your institution administrator to request a custom adapter"
- **Technical Details**: Log specific validation failures for developer review

### Import Errors
- **Data Validation Failures**: Show specific rows/fields that failed validation
- **Conflict Resolution**: Present options based on adapter capabilities
- **Partial Import Success**: Report what succeeded and what failed

### User Education
- **Adapter Purpose**: Explain that adapters are custom-built for each institution
- **File Format Guidance**: Provide examples of compatible file structures
- **Support Channel**: Clear path to request new adapters

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Implement BaseAdapter abstract class
- [ ] Create adapter registry and discovery system
- [ ] Update UI to remove data type dropdown
- [ ] Add file compatibility validation workflow

### Phase 2: Enhanced Validation
- [ ] Implement detailed compatibility checking
- [ ] Add data type detection and reporting
- [ ] Create error messaging system
- [ ] Update user interface with status feedback

### Phase 3: Institution Scoping
- [ ] Implement role-based adapter filtering
- [ ] Add adapter metadata management
- [ ] Create adapter development documentation
- [ ] Deploy institution-specific adapters

### Phase 4: Advanced Features
- [ ] Add adapter versioning system
- [ ] Implement adapter update notifications
- [ ] Create adapter performance monitoring
- [ ] Add usage analytics and reporting

## Technical Specifications

### Adapter Storage
```
adapters/
├── base_adapter.py              # Abstract base class
├── cei_excel_adapter.py         # MockU Excel format handler
├── mocku_csv_adapter.py           # MockU CSV format handler
├── ptu_csv_adapter.py           # PTU CSV format handler
├── rcc_json_adapter.py          # RCC JSON format handler
└── adapter_registry.py          # Adapter discovery and management
```

### Database Schema Extensions
```sql
-- Adapter tracking table
CREATE TABLE import_adapters (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    institution_id VARCHAR(255),
    version VARCHAR(50),
    supported_formats JSON,
    data_types JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

-- Import history with adapter tracking
ALTER TABLE import_history 
ADD COLUMN adapter_id VARCHAR(255),
ADD FOREIGN KEY (adapter_id) REFERENCES import_adapters(id);
```

### API Endpoints
```python
# Adapter management
GET    /api/adapters                    # List available adapters (scoped)
GET    /api/adapters/{id}/info          # Get adapter details
POST   /api/adapters/{id}/validate      # Validate file compatibility
POST   /api/adapters/{id}/preview       # Preview import results

# Import workflow
POST   /api/import/upload               # Upload file
POST   /api/import/validate             # Validate with selected adapter
POST   /api/import/execute              # Execute import
GET    /api/import/status/{id}          # Check import status
```

## Success Metrics

### User Experience
- **Reduced Support Tickets**: Fewer requests for "unsupported format" issues
- **Faster Onboarding**: New institutions can import data immediately after adapter development
- **Higher Success Rate**: Improved import success rate due to format-specific validation

### System Flexibility
- **Institution Coverage**: Each institution has adapters for their unique formats
- **Format Diversity**: Support for Excel, CSV, JSON, and custom formats
- **Scalable Development**: New institutions can be onboarded without system changes

### Developer Efficiency
- **Reusable Framework**: BaseAdapter provides consistent development pattern
- **Clear Requirements**: Adapter specifications guide development process
- **Isolated Changes**: New adapters don't affect existing functionality

## Future Enhancements

### Automated Adapter Generation
- AI-assisted adapter creation from sample files
- Template-based adapter generation for common patterns
- Institution self-service adapter customization tools

### Advanced Validation
- Cross-reference validation between related data types
- Historical data consistency checking
- Real-time format change detection

### Integration Capabilities
- Direct API connections to institution systems
- Scheduled automatic imports
- Real-time data synchronization

## Conflict Resolution Strategies

### `--use-mine` (Keep Existing)
**When to use:** Protecting existing manually-entered data
- Keeps all existing database records unchanged
- Skips conflicting import records
- Logs conflicts for review
- Best for: Incremental updates where database is authoritative

**Example:**
```bash
python import_cli.py --file data.xlsx --adapter cei_excel_format_v1 --use-mine --dry-run
```

### `--use-theirs` (Overwrite with Import)
**When to use:** Import file is the authoritative source
- Overwrites existing data with import values
- Updates conflicting fields
- Maintains audit trail of changes
- Best for: Initial data imports, refreshing from external systems

**Example:**
```bash
python import_cli.py --file institution_data.xlsx --adapter cei_excel_format_v1 --use-theirs
```

### `--manual-review` (Flag for Review)
**When to use:** Critical data that requires human verification
- Identifies conflicts without resolving them
- Creates review queue for administrators
- Provides detailed conflict reports
- Best for: Sensitive data, complex validation scenarios

### `--merge` (Intelligent Merging)
**When to use:** Future enhancement for sophisticated data combining
- Combines data using predefined rules
- Newer timestamps win for dated fields
- Preserves important manual additions
- Best for: Advanced workflows (future implementation)

## Command Line Interface

### Import Commands
```bash
# Standard import with compatibility check
python import_cli.py \
  --file "institution_data.xlsx" \
  --adapter cei_excel_format_v1 \
  --use-theirs \
  --verbose

# Dry-run to preview import results
python import_cli.py \
  --file "test_data.csv" \
  --adapter ptu_csv_enrollment \
  --use-mine \
  --dry-run

# List available adapters for institution
python import_cli.py --list-adapters --institution-id mocku_institution_id

# Validate file compatibility only
python import_cli.py --file sample.xlsx --adapter cei_excel_format_v1 --validate-only
```

### Export Commands
```bash
# Export using institution-specific adapter
python export_cli.py \
  --adapter cei_excel_format_v1 \
  --output "mocku_export.xlsx" \
  --institution-id mocku_institution_id

# Export with specific data types
python export_cli.py \
  --adapter ptu_csv_enrollment \
  --data-types students,enrollments \
  --output "enrollment_export.csv"
```

### Round-Trip Validation
```bash
# Run complete round-trip validation
python scripts/round_trip_validate.py \
  --input tests/data/sanitized_import.xlsx \
  --adapter cei_excel_format_v1 \
  --export build-output/roundtrip_export.xlsx \
  --institution-id mocku_institution_id

# Validate all adapters in CI
python scripts/round_trip_validate.py --all-adapters
```

## API Integration

### Import Endpoints
```javascript
// Upload file with adapter selection
const formData = new FormData();
formData.append('file', dataFile);
formData.append('adapter_id', 'cei_excel_format_v1');
formData.append('conflict_strategy', 'use_theirs');

fetch('/api/import/upload', {
    method: 'POST',
    body: formData
});
```

### Validation Endpoints
```javascript
// Check file compatibility before import
fetch('/api/adapters/cei_excel_format_v1/validate', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(result => {
    if (result.compatible) {
        console.log(`Detected data types: ${result.data_types.join(', ')}`);
        proceedWithImport();
    } else {
        showError(`File incompatible: ${result.error_message}`);
    }
});
```

### Export Endpoints
```javascript
// Request export in institution format
fetch('/api/export/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        adapter_id: 'cei_excel_format_v1',
        data_types: ['courses', 'faculty'],
        institution_id: 'mocku_institution_id'
    })
});
```

## Quality Gates & Validation

### Pre-Import Validation
- **File Format Compatibility**: Adapter validates file structure and format
- **Required Columns**: Checks for all mandatory data fields
- **Data Type Consistency**: Validates data formats (dates, numbers, IDs)
- **Business Rule Validation**: Institution-specific validation rules
- **File Size Limits**: Prevents processing of oversized files

### Post-Import Validation
- **Data Integrity Checks**: Referential consistency between related records
- **Statistical Sanity Checks**: Validates data distributions and ranges
- **Duplicate Detection**: Identifies and handles duplicate records
- **Audit Trail Creation**: Logs all import activities and changes

### Round-Trip Validation (CI)
```yaml
# In .github/workflows/quality-gate.yml
- name: Round-trip Validation
  run: |
    python scripts/round_trip_validate.py --all-adapters
    python scripts/validate_adapter_compatibility.py
```

## Troubleshooting

### Adapter Compatibility Issues
```bash
# List available adapters for your institution
python import_cli.py --list-adapters

# Test adapter with sample data
python import_cli.py --file sample.xlsx --adapter cei_excel_format_v1 --validate-only

# Debug adapter parsing with verbose output
python import_cli.py --file data.xlsx --adapter cei_excel_format_v1 --debug --dry-run
```

### Common Error Messages

#### "File incompatible with [Adapter Name]"
**Cause**: File structure doesn't match adapter expectations
**Solution**: Contact institution admin to request custom adapter for your file format
**Details**: Check logs for specific validation failures

#### "Missing required columns: [column_names]"
**Cause**: Required data columns not found in uploaded file
**Solution**: Add missing columns to file or use different adapter
**Details**: Each adapter documents its required column structure

#### "No adapters available for your institution"
**Cause**: No custom adapters developed for your institution yet
**Solution**: Institution admin should contact system developer to request adapter development
**Timeline**: Custom adapter development typically takes 1-2 weeks

### Round-Trip Validation Failures
```bash
# Run detailed round-trip analysis
python scripts/round_trip_validate.py \
  --input test.xlsx \
  --adapter cei_excel_format_v1 \
  --verbose \
  --diff-output diff_report.txt

# Check for data loss during round-trip
python scripts/compare_import_export.py \
  --original original.xlsx \
  --exported exported.xlsx \
  --adapter cei_excel_format_v1
```

## Best Practices

### For Institution Administrators
1. **Provide Sample Data**: When requesting new adapters, provide representative sample files
2. **Document Requirements**: Clearly specify what data needs to be imported/exported
3. **Test Thoroughly**: Validate adapter functionality with real data before production use
4. **Plan for Updates**: Consider how data formats might change over time

### For System Developers
1. **Start with Compatibility**: Implement file validation before parsing logic
2. **Handle Errors Gracefully**: Provide clear, actionable error messages
3. **Test with Real Data**: Use sanitized versions of actual institution data
4. **Document Assumptions**: Clearly document all data format assumptions
5. **Version Adapters**: Plan for adapter updates as institution needs evolve

### For End Users
1. **Check Compatibility First**: Always validate file compatibility before importing
2. **Use Dry-Run Mode**: Preview import results before committing changes
3. **Monitor Import Results**: Review import logs and error reports
4. **Request Help Early**: Contact institution admin if files don't work with available adapters

---

This adaptive import system transforms the Course Record Updater from a one-size-fits-all solution into a truly flexible platform that can accommodate any institution's unique data formats while maintaining a consistent user experience and providing clear guidance when custom development is needed.
