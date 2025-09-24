# Import/Export System Guide

**Comprehensive guide to the bidirectional Course Data Import/Export System with pluggable adapters for institution-specific data formats**

---

## Overview

The Import/Export System provides a robust, flexible solution for bidirectional data flow with educational institutions. Built around a pluggable adapter architecture, it supports both importing course data from Excel files and exporting data back in institution-specific formats.

### Key Features
- ✅ **Bidirectional Data Flow** - Import AND Export with format preservation
- ✅ **Pluggable Adapter Architecture** - Custom adapters per institution
- ✅ **Multiple Conflict Resolution Strategies**
- ✅ **Dry-run Simulation**
- ✅ **Round-trip Validation** - Automated import→export→diff testing
- ✅ **Comprehensive Validation**
- ✅ **Detailed Reporting**
- ✅ **CLI and API Interfaces**

---

## Adapter Architecture

### Core Concept
Each institution has unique data formats, column structures, and business rules. The system uses **bidirectional adapters** that handle both import parsing and export formatting for specific institutions.

### Available Adapters

#### Default Adapter (`default_adapter`)
**Purpose**: Standard academic data format based on market research
**Use Case**: New institutions, standard implementations, baseline functionality

**Import Format**: Standardized academic Excel structure
**Export Views**:
- **Academic Summary View**: Course-focused export with enrollment and outcomes data
- **Administrative View**: User-focused export with instructor assignments and program data

#### Institution-Specific Adapters
**Purpose**: Custom formats tailored to specific institution requirements
**Examples**:
- `cei_excel_adapter`: Handles CEI's specific FA2024 results format
- `university_x_adapter`: Custom format for University X
- `business_school_adapter`: Specialized for business program requirements

---

## Bidirectional Workflow

### Import Process
```
Excel File → Adapter.parse_row() → Validation → Conflict Resolution → Database
```

### Export Process  
```
Database → Adapter.format_data() → Excel Generation → Download/API Response
```

### Round-trip Validation
```
Original File → Import → Database → Export → Generated File → Diff Comparison
```

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
python import_cli.py --file data.xlsx --adapter default_adapter --use-mine --dry-run
```

### `--use-theirs` (Overwrite with Import)
**When to use:** Import file is the authoritative source
- Overwrites existing data with import values
- Updates conflicting fields
- Maintains audit trail of changes
- Best for: Initial data imports, refreshing from external systems

**Example:**
```bash
python import_cli.py --file institution_data.xlsx --adapter custom_adapter --use-theirs
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

---

## Usage Examples

### Default Adapter Workflows

#### Standard Import
```bash
# Import using default academic format
python import_cli.py \
  --file "academic_data.xlsx" \
  --adapter default_adapter \
  --use-theirs \
  --verbose
```

#### Export Academic Summary
```bash
# Export in academic summary format
python export_cli.py \
  --adapter default_adapter \
  --view academic_summary \
  --output "exported_academic_data.xlsx" \
  --institution-id "institution-123"
```

#### Export Administrative View
```bash
# Export in administrative format
python export_cli.py \
  --adapter default_adapter \
  --view administrative \
  --output "admin_export.xlsx" \
  --institution-id "institution-123"
```

### Institution-Specific Workflows

#### Custom Institution Import
```bash
python import_cli.py \
  --file "institution_specific_data.xlsx" \
  --adapter institution_x_adapter \
  --use-theirs \
  --dry-run
```

#### Custom Institution Export
```bash
python export_cli.py \
  --adapter institution_x_adapter \
  --output "institution_format_export.xlsx" \
  --institution-id "institution-x"
```

---

## Round-Trip Validation System

### Purpose
Guarantees that data imported through any adapter can be exported back in the same format without loss of information or structure.

### Test Data Management
```bash
# Create sanitized test fixture from real data
python scripts/sanitize_test_data.py \
  --input "real_institution_data.xlsx" \
  --output "tests/data/sanitized_import.xlsx" \
  --adapter institution_adapter
```

### Automated Validation
```bash
# Run complete round-trip validation
python scripts/round_trip_validate.py \
  --input tests/data/sanitized_import.xlsx \
  --adapter default_adapter \
  --export build-output/roundtrip_export.xlsx \
  --institution-id test-institution
```

### CI Integration
The round-trip validation runs automatically in CI to catch any regressions in the import/export pipeline:

```yaml
# In .github/workflows/quality-gate.yml
- name: Round-trip Validation
  run: python scripts/round_trip_validate.py --all-adapters
```

---

## API Integration

### Import Endpoints
```javascript
// Upload Excel file with specific adapter
const formData = new FormData();
formData.append('file', excelFile);
formData.append('adapter_name', 'default_adapter');
formData.append('conflict_strategy', 'use_theirs');

fetch('/api/import/excel', {
    method: 'POST',
    body: formData
});
```

### Export Endpoints
```javascript
// Request export in specific format
fetch('/api/export/excel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        adapter_name: 'default_adapter',
        view: 'academic_summary',
        institution_id: 'inst-123'
    })
});
```

### Validation Endpoints
```javascript
// Validate file before import
fetch('/api/import/validate', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(validation => {
    if (validation.valid) {
        // File is compatible with selected adapter
        proceedWithImport();
    }
});
```

---

## Adapter Development

### Creating Custom Adapters

#### Import Adapter Interface
```python
class CustomInstitutionAdapter(BaseAdapter):
    """Custom adapter for Institution X data format"""
    
    def parse_excel_row(self, row, institution_id):
        """Parse a single Excel row into normalized entities"""
        return {
            'course': self.extract_course_data(row, institution_id),
            'user': self.extract_instructor_data(row, institution_id),
            'term': self.extract_term_data(row, institution_id),
            'section': self.extract_section_data(row, institution_id)
        }
    
    def format_export_data(self, data, view='default'):
        """Format database data for export"""
        if view == 'custom_view':
            return self.format_custom_view(data)
        return self.format_standard_view(data)
```

#### Export Adapter Interface
```python
class CustomExportAdapter(BaseExportAdapter):
    """Handle export formatting for Institution X"""
    
    def get_available_views(self):
        """Return list of available export views"""
        return ['standard', 'detailed', 'summary']
    
    def format_data_for_view(self, data, view):
        """Format data according to specified view"""
        formatters = {
            'standard': self.format_standard_view,
            'detailed': self.format_detailed_view,
            'summary': self.format_summary_view
        }
        return formatters[view](data)
```

### Configuration-Driven Mapping
```yaml
# adapters/configs/institution_x.yaml
adapter_name: "institution_x_adapter"
import_config:
  column_mapping:
    course_identifier: "Course_Code"
    course_name: "Course_Title"
    instructor: "Faculty_Name"
    term: "Academic_Term"
  validation_rules:
    course_format: "^[A-Z]{2,4}[0-9]{3,4}$"
    max_enrollment: 500

export_config:
  views:
    standard:
      columns: ['course_code', 'title', 'instructor', 'enrollment']
    detailed:
      columns: ['course_code', 'title', 'instructor', 'enrollment', 'outcomes', 'assessments']
  formatting:
    date_format: "%Y-%m-%d"
    number_format: "0.00"
```

---

## Default Adapter Specifications

### Academic Summary View (Default Export)
**Target Audience**: Academic administrators, program coordinators
**Content Focus**: Course performance, enrollment, learning outcomes

**Columns**:
- Course Information (Number, Title, Department)
- Enrollment Data (Total, Active, Completion Rate)
- Learning Outcomes Summary
- Assessment Results Overview
- Instructor Assignment

### Administrative View (Alternative Export)
**Target Audience**: HR, institutional research, compliance
**Content Focus**: Instructor workload, program assignments, institutional metrics

**Columns**:
- Instructor Information (Name, Email, Department)
- Course Assignments (Load, Schedule)
- Program Affiliations
- Student Counts by Program
- Term/Semester Data

---

## Data Sanitization

### Sanitization Script
```bash
# Create sanitized test data preserving format
python scripts/sanitize_test_data.py \
  --input "sensitive_data.xlsx" \
  --output "tests/data/sanitized_test.xlsx" \
  --preserve-structure \
  --anonymize-names \
  --fake-emails
```

### Sanitization Rules
- **Names**: Replace with realistic fake names maintaining demographic distribution
- **Emails**: Generate fake emails preserving domain structure
- **Student IDs**: Replace with sequential test IDs
- **Grades/Scores**: Maintain statistical distribution but randomize individual values
- **Structure**: Preserve all column headers, data types, and relationships

---

## Quality Gates & Validation

### Pre-Import Validation
- File format compatibility with selected adapter
- Required columns presence
- Data type consistency
- Business rule validation

### Post-Import Validation
- Data integrity checks
- Referential consistency
- Statistical sanity checks

### Round-trip Validation (CI)
- Import test fixture
- Export using same adapter
- Byte-level comparison of structure
- Column mapping verification
- Data preservation validation

---

## Best Practices

### Adapter Selection
1. **Start with default adapter** for standard academic formats
2. **Create custom adapter** only when default doesn't meet 80%+ of requirements
3. **Validate round-trip** before deploying any new adapter
4. **Document adapter requirements** clearly for maintenance

### Development Workflow
1. **Implement default adapter first** - establishes baseline functionality
2. **Create sanitized test data** from real institution files
3. **Develop custom adapter** using sanitized data
4. **Validate bidirectional flow** with round-trip testing
5. **Add to CI pipeline** for regression protection

### Data Management
1. **Never commit real institutional data** to version control
2. **Use sanitization scripts** to create test fixtures
3. **Maintain format fidelity** during sanitization
4. **Test with realistic data volumes** for performance validation

---

## Troubleshooting

### Adapter Issues
```bash
# List available adapters
python import_cli.py --list-adapters

# Test adapter with sample data
python import_cli.py --file sample.xlsx --adapter custom_adapter --validate-only

# Debug adapter parsing
python import_cli.py --file data.xlsx --adapter custom_adapter --debug --dry-run
```

### Round-trip Failures
```bash
# Run detailed round-trip analysis
python scripts/round_trip_validate.py \
  --input test.xlsx \
  --adapter custom_adapter \
  --verbose \
  --diff-output diff_report.txt
```

### Export Issues
```bash
# Test export functionality
python export_cli.py \
  --adapter default_adapter \
  --view academic_summary \
  --dry-run \
  --verbose
```

This adapter-based architecture ensures the system can handle diverse institutional requirements while maintaining data integrity and providing standardized interfaces for common academic data exchange patterns.