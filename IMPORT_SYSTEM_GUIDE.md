# Import System Guide

**Comprehensive guide to the Course Data Import System with conflict resolution and dry-run capabilities**

---

## Overview

The Import System provides a robust, flexible solution for importing course data from Excel files with sophisticated conflict resolution and validation. Built for CEI's specific needs while being extensible for other customers.

### Key Features
- ✅ **Multiple Conflict Resolution Strategies**
- ✅ **Dry-run Simulation** 
- ✅ **Comprehensive Validation**
- ✅ **Detailed Reporting**
- ✅ **CLI and API Interfaces**
- ✅ **Extensible Adapter Pattern**

---

## Conflict Resolution Strategies

### `--use-mine` (Keep Existing)
**When to use:** Protecting existing manually-entered data
- Keeps all existing database records unchanged
- Skips conflicting import records
- Logs conflicts for review
- Best for: Incremental updates where database is authoritative

**Example:**
```bash
python import_cli.py --file data.xlsx --use-mine --dry-run
```

### `--use-theirs` (Overwrite with Import) 
**When to use:** Import file is the authoritative source
- Overwrites existing data with import values
- Updates conflicting fields
- Maintains audit trail of changes
- Best for: CEI's initial data import, refreshing from external systems

**Example:**
```bash
python import_cli.py --file cei_2024_data.xlsx --use-theirs
```

### `--manual-review` (Flag for Review)
**When to use:** Critical data that requires human verification
- Identifies conflicts without resolving them
- Creates review queue for administrators
- Provides detailed conflict reports
- Best for: Sensitive data, complex validation scenarios

**Example:**
```bash
python import_cli.py --file data.xlsx --manual-review --report-file conflicts.txt
```

### `--merge` (Intelligent Merging)
**When to use:** Future enhancement for sophisticated data combining
- Combines data using predefined rules
- Newer timestamps win for dated fields
- Preserves important manual additions
- Best for: Advanced workflows (future implementation)

---

## Usage Examples

### CEI-Specific Workflows

#### Initial Data Import (First Time)
```bash
# Import CEI's 1,543 CLO records
python import_cli.py \
  --file "2024FAresults.xlsx" \
  --use-theirs \
  --adapter cei_excel_adapter \
  --verbose \
  --report-file "cei_import_report.txt"
```

#### Dry Run Validation
```bash
# Test import without making changes
python import_cli.py \
  --file "2024FAresults.xlsx" \
  --use-theirs \
  --dry-run \
  --verbose
```

#### Incremental Updates
```bash
# Protect existing manual entries
python import_cli.py \
  --file "updated_courses.xlsx" \
  --use-mine \
  --report-file "conflicts_to_review.txt"
```

#### Semester Refresh
```bash
# Update with new semester data
python import_cli.py \
  --file "spring_2025_data.xlsx" \
  --use-theirs \
  --adapter cei_excel_adapter
```

### Multi-Customer Workflows

#### Customer A - Business School
```bash
python import_cli.py \
  --file "business_courses.xlsx" \
  --use-theirs \
  --adapter business_school_adapter \
  --dry-run
```

#### Customer B - Nursing Program
```bash
python import_cli.py \
  --file "nursing_assessments.xlsx" \
  --manual-review \
  --adapter nursing_program_adapter \
  --verbose
```

---

## API Integration

### Web Interface Upload
```javascript
// Upload Excel file via web interface
const formData = new FormData();
formData.append('file', excelFile);
formData.append('conflict_strategy', 'use_theirs');
formData.append('dry_run', 'false');
formData.append('adapter_name', 'cei_excel_adapter');

fetch('/api/import/excel', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(result => {
    console.log('Import result:', result);
});
```

### Validation Before Import
```javascript
// Validate file format first
const formData = new FormData();
formData.append('file', excelFile);
formData.append('adapter_name', 'cei_excel_adapter');

fetch('/api/import/validate', {
    method: 'POST', 
    body: formData
})
.then(response => response.json())
.then(validation => {
    if (validation.validation.valid) {
        // Proceed with actual import
        performImport();
    } else {
        // Show validation errors
        showErrors(validation.validation.errors);
    }
});
```

---

## Technical Architecture

### Import Flow
```
Excel File → File Validation → Row Processing → Conflict Detection → Resolution → Database Update
     ↓              ↓              ↓               ↓               ↓             ↓
   .xlsx        Format Check    Parse Entities   Compare Data   Apply Strategy  Save/Skip
```

### Entity Processing
```
Single Row → Course + User + Term + Section + Outcomes
    ↓           ↓      ↓      ↓       ↓         ↓
  Parse     Validate Parse Validate Parse   Validate
    ↓           ↓      ↓      ↓       ↓         ↓
  Create    Conflict User Conflict Section  Conflict
           Detection    Detection     Detection
```

### Conflict Resolution Engine
```python
# Example conflict detection and resolution
conflict = ConflictRecord(
    entity_type='course',
    entity_key='ACC-201',
    field_name='course_title',
    existing_value='Accounting Principles',
    import_value='Principles of Accounting',
    resolution=None
)

# Apply strategy
if strategy == ConflictStrategy.USE_THEIRS:
    # Update database with import value
    update_course(course_id, {'course_title': import_value})
    conflict.resolution = 'used_import'
```

---

## Data Mapping (CEI-Specific)

### Excel Column Mapping
```python
# CEI's 2024FAresults.xlsx structure
COLUMN_MAPPING = {
    'course': 'course_number',          # "ACC 201" → "ACC-201"
    'course_title': 'course_title',     # Course name
    'Faculty Name': 'instructor_name',   # Full instructor name
    'Term': 'term_name',                # "2024 Fall"
    'Section': 'section_number',        # "001"
    'Enrollment': 'enrollment_count',   # Number of students
    'cllo_text': 'clo_description',     # CLO text
    # ... additional mappings
}
```

### Department Extraction
```python
# Automatic department assignment from course prefix
DEPARTMENT_MAPPING = {
    'ACC': 'Business',
    'BUS': 'Business', 
    'ECON': 'Business',
    'NURS': 'Nursing',
    'BIOL': 'Science',
    'MATH': 'Mathematics',
    'ENG': 'English'
}
```

### User Generation
```python
# Automatic user creation from instructor names
"John Smith" → {
    'email': 'john.smith@cei.edu',
    'first_name': 'John',
    'last_name': 'Smith',
    'role': 'instructor',
    'department': 'Business'  # Derived from course
}
```

---

## Validation Rules

### File-Level Validation
- ✅ Excel format (.xlsx, .xls)
- ✅ Required columns present
- ✅ No completely empty rows
- ✅ Data type consistency

### Business Logic Validation
- ✅ Course numbers follow format (e.g., "ACC-201")
- ✅ Term names are valid (e.g., "2024 Fall")
- ✅ Enrollment numbers are reasonable (0-1000)
- ✅ Email addresses are properly formatted
- ✅ CLO numbers follow conventions

### Referential Integrity
- ✅ Courses exist before creating sections
- ✅ Users exist before assignment
- ✅ Terms are valid before section creation
- ✅ No orphaned records

---

## Error Handling & Reporting

### Error Categories
```python
# Error types and handling
ERRORS = {
    'validation_error': 'Invalid data format or business rules',
    'conflict_error': 'Data conflicts requiring resolution', 
    'database_error': 'Database connection or operation failure',
    'file_error': 'File access or format issues',
    'adapter_error': 'Import adapter configuration problems'
}
```

### Report Structure
```json
{
  "success": true,
  "dry_run": false,
  "statistics": {
    "records_processed": 1543,
    "records_created": 1200,
    "records_updated": 300,
    "records_skipped": 43,
    "conflicts_detected": 15,
    "conflicts_resolved": 15,
    "execution_time": 45.2
  },
  "errors": [],
  "warnings": ["Minor formatting issues corrected"],
  "conflicts": [
    {
      "entity_type": "course",
      "entity_key": "ACC-201", 
      "field_name": "course_title",
      "existing_value": "Accounting Principles",
      "import_value": "Principles of Accounting",
      "resolution": "used_import"
    }
  ]
}
```

---

## Extending for Other Customers

### Creating Custom Adapters
```python
# Example: Create adapter for new customer
class CustomSchoolAdapter:
    def parse_excel_row(self, row):
        # Customer-specific column mapping
        return {
            'course': self.extract_course_data(row),
            'user': self.extract_instructor_data(row),
            'term': self.extract_term_data(row)
        }
    
    def extract_course_data(self, row):
        # Custom business logic for this school
        return {
            'course_number': row['Course Code'],
            'course_title': row['Course Name'],
            'department': self.map_department(row['Dept'])
        }
```

### Configuration-Driven Mapping
```yaml
# customer_config.yaml
customer: "university_x"
adapter_name: "university_x_adapter"
column_mapping:
  course_identifier: "Course_ID"
  course_name: "Title"
  instructor: "Professor"
  term: "Semester"
department_mapping:
  "COMP": "Computer Science"
  "MATH": "Mathematics"
validation_rules:
  course_format: "^[A-Z]{4}[0-9]{3}$"
  max_enrollment: 500
```

---

## Best Practices

### Before Import
1. **Always run dry-run first** to identify issues
2. **Validate file format** using validation endpoint
3. **Backup database** before major imports
4. **Review conflict strategy** based on data sensitivity

### During Import
1. **Monitor progress** in verbose mode
2. **Check for errors** in real-time
3. **Stop on critical failures** rather than continuing
4. **Save detailed reports** for audit trail

### After Import
1. **Review import reports** for data quality
2. **Validate key records** manually
3. **Resolve flagged conflicts** promptly
4. **Update documentation** with lessons learned

### CEI-Specific Recommendations
1. **Use --use-theirs for initial import** of 1,543 CLO records
2. **Use --use-mine for incremental updates** to protect manual entries
3. **Always run --dry-run first** on production data
4. **Save reports** for Leslie's review and approval
5. **Test with sample data** before full import

---

## Troubleshooting

### Common Issues

#### "File not found" Error
```bash
# Check file path and permissions
ls -la path/to/file.xlsx
python import_cli.py --file "$(pwd)/data.xlsx" --dry-run
```

#### "No records processed" 
```bash
# Validate file format
python import_cli.py --file data.xlsx --validate-only --verbose
```

#### "Conflict resolution failed"
```bash
# Review conflicts first
python import_cli.py --file data.xlsx --manual-review --verbose
```

#### "Database connection error"
```bash
# Check Firestore emulator (development)
export FIRESTORE_EMULATOR_HOST=localhost:8086
```

### Debug Mode
```bash
# Maximum verbosity for troubleshooting
python import_cli.py \
  --file data.xlsx \
  --dry-run \
  --verbose \
  --report-file debug_report.txt
```

---

## Production Deployment

### Environment Configuration
```bash
# Production settings
export FLASK_ENV=production
export FIRESTORE_PROJECT_ID=cei-course-management
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Import with production safety
python import_cli.py \
  --file production_data.xlsx \
  --use-theirs \
  --report-file "$(date +%Y%m%d)_import_report.txt"
```

### Monitoring & Alerts
- Set up logging for all import operations
- Monitor import success/failure rates
- Alert on unusual conflict patterns
- Track import performance metrics

This comprehensive import system provides CEI with a reliable, auditable way to manage their course data while being flexible enough for other educational institutions.
