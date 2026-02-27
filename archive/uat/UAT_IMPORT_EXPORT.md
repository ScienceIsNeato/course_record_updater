# Import/Export UAT Guide

**User Acceptance Testing for Data Import and Export Functionality**

## Document Information

- **Version**: 2.0
- **Date**: October 2025
- **Purpose**: Validate import/export functionality with specific, measurable test criteria
- **Target**: Post-quality-gate validation - catching bugs that automated tests miss
- **Philosophy**: Surgical precision over vague "looks good" checks

---

## 🎯 Testing Philosophy

### What This UAT Validates

- **End-to-end data flows** that unit tests can't catch
- **UI/UX issues** in the import/export workflows
- **Data integrity** across the full import→display→export cycle
- **Edge cases** with real-world data formats
- **Multi-entity relationships** (courses→sections→instructors→terms)

### What This UAT Doesn't Cover

- Individual function logic (covered by unit tests)
- Security vulnerabilities (covered by SonarCloud/Bandit)
- Performance at scale (covered by integration tests)
- Browser compatibility (covered by automated Playwright tests)

---

## 📋 Test Environment Setup

### Prerequisites

```bash
# 1. Ensure fresh database state
cd /Users/pacey/Documents/SourceCode/course_record_updater
source venv/bin/activate
source .envrc

# 2. Backup existing database (if needed)
cp course_records.db course_records.db.backup

# 3. Start server
./restart_server.sh

# 4. Verify server health
curl http://localhost:3001/api/health
```

### Test Data Files

**IMPORTANT**: Create controlled test data using Generic CSV adapter for test isolation.

**Available Adapters**:

1. **Generic CSV Adapter** (`generic_csv_v1`):
   - Bidirectional (import + export)
   - ZIP file containing normalized CSVs
   - Institution-agnostic
   - **Use this for UAT testing**

2. **MockU Excel Adapter** (`cei_excel_format_v1`):
   - Import-only (no export)
   - Customer-specific format
   - `.xlsx` files only
   - Not covered in this UAT (customer-specific)

**Test Data Strategy**:

- Create minimal ZIP of CSVs with known, predictable values
- Import via Generic CSV adapter
- Test against this controlled dataset
- No dependency on external customer files

### Test Accounts

Login as **Institution Admin** for these tests:

- **Email**: `sarah.admin@mocku.test`
- **Password**: `InstitutionAdmin123!`
- **Why**: Institution admins have import/export permissions

---

## 🧪 SCENARIO 1: Generic CSV Import - End-to-End Data Flow

### Test Objective

Validate that imported Generic CSV data (ZIP format) correctly populates ALL entity types and is visible in appropriate UI views.

---

### **TC-IE-001: Dry Run Import Validation**

**Purpose**: Confirm validation catches issues WITHOUT modifying database

**Test File**: Create controlled `test_import.zip` with known CSV data

**Steps**:

1. Login as `sarah.admin@mocku.test`
2. Navigate to dashboard
3. Locate "Data Management" panel (should be Panel 4 or 5)
4. Click **"Import"** button (opens file picker)
5. Upload `test_import.zip` (ZIP containing normalized CSVs)
6. System auto-detects **"Generic CSV Format (ZIP)"** adapter
7. Enable **"Dry Run"** checkbox
8. Click **"Validate"**
9. Wait for validation results modal

**Expected Results - Validation Summary**:

- ✅ **Status**: "Validation successful" message displayed
- ✅ **Records Found**: Shows count > 0 (e.g., "150 records processed")
- ✅ **Potential Conflicts**: Shows specific conflict types if any duplicates
- ✅ **Errors**: Empty list OR specific, actionable error messages
- ✅ **Warnings**: List of non-blocking issues (e.g., "Instructor email missing for 3 sections")
- ✅ **File Info**: Displays filename and adapter used

**Validation Details to Check**:

- Count of **Courses** to be created (expect ~40-50 unique course numbers)
- Count of **Instructors** to be created (expect ~15-20 unique emails)
- Count of **Terms** to be created (expect 1-2 terms like "FA2024", "SP2025")
- Count of **Sections** to be created (expect ~60-80 course sections)
- Count of **Course Offerings** to be created (one per course+term combination)

**Database Verification** (dry run should NOT modify):

```bash
# Open SQLite database and verify NO new records were created
python -c "
from database_service import get_all_courses, get_all_users, get_all_sections
print(f'Courses: {len(get_all_courses() or [])}')
print(f'Users: {len(get_all_users() or [])}')
print(f'Sections: {len(get_all_sections() or [])}')
"
# Counts should match PRE-import baseline (dry run = no changes)
```

**Critical Assertions**:

- [ ] Validation modal appears within 10 seconds
- [ ] No JavaScript errors in browser console
- [ ] Database record counts UNCHANGED after dry run
- [ ] Validation results match expected entity counts
- [ ] File upload progress indicator works

---

### **TC-IE-002: Successful Import with Conflict Resolution**

**Purpose**: Verify actual import creates correct database records

**Prerequisites**: TC-IE-001 passed

**Steps**:

1. Same setup as TC-IE-001
2. Upload same file: `test_import.zip`
3. Adapter: Auto-detected **"Generic CSV Format (ZIP)"**
4. **DISABLE "Dry Run"** checkbox
5. Conflict Strategy: **"Use theirs (overwrite)"**
6. Click **"Import"**
7. Wait for import completion modal

**Expected Results - Import Summary**:

- ✅ **Status**: "Import successful" message
- ✅ **Records Processed**: Matches validation count
- ✅ **Conflicts Resolved**: Shows count of overwrites (may be 0 on first import)
- ✅ **Entities Created**: Breakdown by type (courses, users, terms, sections, offerings)
- ✅ **Timestamp**: Shows import completion time

**Database Verification** (import SHOULD modify):

```bash
python -c "
from database_service import get_all_courses, get_all_users, get_all_sections, get_active_terms
courses = get_all_courses() or []
users = get_all_users() or []
sections = get_all_sections() or []
terms = get_active_terms() or []

print(f'✅ Courses: {len(courses)} (expect ~40-50)')
print(f'✅ Users: {len(users)} (expect ~15-20)')
print(f'✅ Sections: {len(sections)} (expect ~60-80)')
print(f'✅ Terms: {len(terms)} (expect 1-2)')

# Spot check specific course
math101 = [c for c in courses if 'MATH-101' in c.get('course_number', '')]
if math101:
    print(f'✅ MATH-101 imported: {math101[0].get(\"course_title\")}')
else:
    print('❌ MATH-101 NOT FOUND')
"
```

**Critical Assertions**:

- [ ] Database record counts INCREASED after import
- [ ] At least one course with prefix "MATH-" exists
- [ ] At least one course with prefix "ENG-" exists (if in test data)
- [ ] At least one instructor user with role='instructor'
- [ ] At least one term with name containing "FA2024" or "2024FA"
- [ ] Import modal shows success message
- [ ] No HTTP 500 errors in network tab

---

### **TC-IE-003: Imported Course Visibility in Courses List**

**Purpose**: Validate imported courses appear in UI with correct attributes

**Prerequisites**: TC-IE-002 passed (data imported)

**Steps**:

1. From dashboard, navigate to **"Courses"** menu item
2. Verify course list loads
3. Search for **"MATH-101"** (or first course from test file)
4. Click on course row to view details

**Expected Results - Courses List View**:

- ✅ **List Loads**: Course table populates within 5 seconds
- ✅ **Course Count**: Matches import summary (~40-50 courses)
- ✅ **Required Columns Visible**:
  - Course Number (e.g., "MATH-101")
  - Course Title (e.g., "College Algebra")
  - Department (e.g., "Mathematics" or "MATH")
  - Credits (e.g., "3" or "4")
  - Program (if assigned to default "Unclassified" program)

**Expected Results - Course Details View**:

- ✅ **Course Metadata**:
  - Course Number: Exact match from Excel (e.g., "MATH-101")
  - Course Title: Exact match from Excel
  - Department: Derived from course prefix or explicit column
  - Credits: Integer value (3 or 4 typically)
  - Institution: "MockU" or institution name
- ✅ **Related Entities**:
  - **Sections**: List of sections for this course (1+ sections)
  - **Instructors**: List of assigned instructors (may be via sections)
  - **Terms**: List of terms where course is offered
  - **Program Assignment**: Shows "Unclassified" or specific program

**Specific Data Validations**:

```bash
# Manual UI checks:
# 1. Course number format matches Excel (no extra spaces/formatting)
# 2. Course title is human-readable (not corrupted encoding)
# 3. Department name is consistent across similar courses
# 4. Credits are reasonable integers (not decimals like 3.5)
```

**Critical Assertions**:

- [ ] At least 10 courses visible in list
- [ ] Course numbers match Excel file exactly
- [ ] Course titles are not empty or "[Untitled]"
- [ ] Departments are not "Unknown" or null
- [ ] Can click a course and see details without errors

---

### **TC-IE-004: Imported Instructor Visibility in Users List**

**Purpose**: Validate imported instructors exist with correct roles and metadata

**Prerequisites**: TC-IE-002 passed

**Steps**:

1. From dashboard, navigate to **"Users"** menu item
2. Filter by role: **"Instructor"**
3. Verify instructor list loads
4. Search for specific instructor email from test file (e.g., "john.instructor@mocku.test")
5. Click on instructor row to view profile/details

**Expected Results - Users List View**:

- ✅ **List Loads**: User table populates within 5 seconds
- ✅ **Instructor Count**: Matches import summary (~15-20 instructors)
- ✅ **Required Columns Visible**:
  - Email (primary identifier)
  - First Name (parsed from email or provided)
  - Last Name (parsed from email or provided)
  - Role Badge: "Instructor"
  - Department (if available from Excel)
  - Account Status: "imported" or "needs_email"

**Expected Results - Instructor Details**:

- ✅ **User Metadata**:
  - Email: Valid email format
  - Full Name: First + Last not empty
  - Role: "instructor" (lowercase in database)
  - Institution: MockU institution ID
  - Account Status: "imported" (may need activation)
- ✅ **Related Data**:
  - **Sections Taught**: List of assigned sections (if any)
  - **Department**: Matches course department (if available)

**Specific Validations**:

- [ ] No instructors with missing emails (unless marked "needs_email")
- [ ] No duplicate instructor records (same email twice)
- [ ] Instructor names are not "Unknown Instructor" or placeholders
- [ ] Each instructor has at least one section assignment (check in sections view)

**Critical Assertions**:

- [ ] At least 5 instructors visible in filtered list
- [ ] All instructors have valid email addresses
- [ ] Role badges display "Instructor" (not "Student" or blank)
- [ ] No HTTP errors when loading user details

---

### **TC-IE-005: Imported Section Visibility in Sections Table**

**Purpose**: Validate imported sections show correct course/instructor/term relationships

**Prerequisites**: TC-IE-002 passed

**Steps**:

1. From dashboard, navigate to **"Sections"** menu or view sections panel
2. Use filters to narrow down:
   - **Term**: "FA2024" (or term from test file)
   - **Course**: "MATH-101" (or specific course)
   - **Status**: "Active"
3. Verify section list loads with filters applied
4. Click on a section row to view details

**Expected Results - Sections List View**:

- ✅ **List Loads**: Section table populates within 5 seconds
- ✅ **Section Count**: Matches import summary (~60-80 sections)
- ✅ **Required Columns Visible**:
  - Course Number (e.g., "MATH-101")
  - Section Number (e.g., "001", "002")
  - Term (e.g., "FA2024")
  - Instructor Name (linked to user)
  - Enrollment Count (e.g., "25 students")
  - Status ("Active")

**Expected Results - Section Details View**:

- ✅ **Section Metadata**:
  - Course: Matches a valid course from courses table
  - Section Number: Sequential (001, 002, etc.) - NOT UUIDs!
  - Term: Matches a valid term from terms table
  - Instructor: Matches a valid instructor from users table
  - Enrollment: Integer count (0-50 typically)
  - Status: "active" or "Active"
- ✅ **Relationships Intact**:
  - Clicking instructor name navigates to instructor profile
  - Clicking course number navigates to course details
  - Term filter correctly narrows results

**Specific Validations**:

```bash
# Database integrity check:
python -c "
from database_service import get_all_sections, get_course_by_id, get_user_by_id
sections = get_all_sections() or []
print(f'Total sections: {len(sections)}')

# Check first 3 sections for referential integrity
for section in sections[:3]:
    course_id = section.get('course_id')
    instructor_id = section.get('instructor_id')
    term_name = section.get('term_name')

    course = get_course_by_id(course_id) if course_id else None
    instructor = get_user_by_id(instructor_id) if instructor_id else None

    print(f'Section {section.get(\"section_number\")}: Course={bool(course)}, Instructor={bool(instructor)}, Term={term_name}')
"
```

**Critical Assertions**:

- [ ] At least 10 sections visible in list
- [ ] Section numbers are human-readable (001, 002, NOT UUIDs)
- [ ] Every section has a valid course reference
- [ ] Every section has a valid term reference
- [ ] Enrollment counts are reasonable integers (0-100)
- [ ] No sections with NULL instructor_id (unless allowed by business rules)

---

### **TC-IE-006: Imported Term Visibility**

**Purpose**: Validate terms were created and formatted correctly

**Prerequisites**: TC-IE-002 passed

**Steps**:

1. From dashboard or sections view, check **Term dropdown filter**
2. Open dropdown and view available terms
3. Note format of term names

**Expected Results**:

- ✅ **Term Dropdown Populates**: Shows at least 1 term
- ✅ **Term Format**: Should be "FA2024", "SP2025", etc. (NOT "2024FA" MockU format)
- ✅ **Terms Match Import**: Term count matches validation summary
- ✅ **Chronological Order**: Terms sorted newest first (FA2024 before FA2023)

**Database Verification**:

```bash
python -c "
from database_service import get_active_terms
terms = get_active_terms() or []
print(f'Active terms: {len(terms)}')
for term in terms:
    print(f'  - {term.get(\"name\")} (ID: {term.get(\"id\")})')
"
```

**Critical Assertions**:

- [ ] At least 1 term exists
- [ ] Term names follow standard format (FA/SP/SU + 4-digit year)
- [ ] Terms are not duplicated (no "FA2024" AND "2024FA")
- [ ] Term IDs are valid (not NULL or empty strings)

---

### **TC-IE-007: Import Conflict Resolution (Duplicate Data)**

**Purpose**: Validate re-importing the same file handles conflicts correctly

**Prerequisites**: TC-IE-002 passed (initial import complete)

**Steps**:

1. Navigate back to "Data Management" panel
2. Upload **THE SAME FILE** again: `2024FA_test_data.xlsx`
3. Adapter: "MockU Excel Format"
4. Conflict Strategy: **"Use theirs (overwrite)"**
5. **Disable "Dry Run"**
6. Click **"Import"**
7. Wait for completion

**Expected Results - Conflict Resolution**:

- ✅ **Status**: "Import successful" message
- ✅ **Conflicts Detected**: Shows count > 0 (all records are duplicates)
- ✅ **Resolution Strategy Applied**: "Overwrite existing records"
- ✅ **Database Integrity**: No duplicate records created
- ✅ **Record Counts Stable**: Course/user/section counts unchanged

**Database Verification** (counts should be STABLE, not doubled):

```bash
python -c "
from database_service import get_all_courses, get_all_users, get_all_sections
print(f'Courses: {len(get_all_courses() or [])} (should be unchanged)')
print(f'Users: {len(get_all_users() or [])} (should be unchanged)')
print(f'Sections: {len(get_all_sections() or [])} (should be unchanged)')
"
```

**Critical Assertions**:

- [ ] Import completes successfully (no errors)
- [ ] Database record counts DID NOT DOUBLE
- [ ] No duplicate courses with same course_number
- [ ] No duplicate users with same email
- [ ] Import modal shows "X conflicts resolved"

---

### **TC-IE-008: Import Error Handling (Malformed File)**

**Purpose**: Validate graceful handling of invalid Excel files

**Test File**: Create a **malformed Excel file** for this test:

- Option 1: Empty Excel file (no headers, no data)
- Option 2: Excel with wrong columns (no "course" column)
- Option 3: Non-Excel file renamed to `.xlsx` (e.g., text file)

**Steps**:

1. Navigate to "Data Management" panel
2. Upload malformed file
3. Adapter: "MockU Excel Format"
4. Click **"Validate"** or **"Import"**

**Expected Results - Error Handling**:

- ✅ **Validation Fails**: Error message displayed in modal
- ✅ **Specific Error**: NOT generic "Import failed" - should say:
  - "Missing required columns: course, email, Term" OR
  - "Cannot read Excel file: Invalid format" OR
  - "File is empty"
- ✅ **No Database Changes**: No partial imports
- ✅ **User Can Retry**: Modal allows closing and trying again

**Critical Assertions**:

- [ ] Error message is actionable (tells user what's wrong)
- [ ] No HTTP 500 errors (should be handled gracefully as 400)
- [ ] Database unchanged (no orphaned records)
- [ ] Can immediately upload a valid file without reloading page

---

## 📤 SCENARIO 2: Generic CSV Export - Data Integrity Validation

### Test Objective

Validate that exported Generic CSV files (ZIP format) contain complete, accurate data that matches the database.

---

### **TC-IE-101: Export All Data via Generic CSV**

**Purpose**: Verify Generic CSV export generates valid ZIP with complete normalized data

**Prerequisites**: TC-IE-002 passed (data imported)

**Steps**:

1. From dashboard, navigate to "Data Management" panel
2. Locate **"Export"** button
3. Click **"Export"** (no format selection - Generic CSV always exports as ZIP)
4. Wait for file download
5. Open downloaded ZIP file

**Expected Results - Export File**:

- ✅ **File Downloads**: `.zip` file downloads within 10 seconds
- ✅ **Filename Format**: `export_YYYYMMDD_HHMMSS.zip` (timestamped)
- ✅ **ZIP Opens Successfully**: Valid ZIP structure, no corruption
- ✅ **CSV Files Present**: ZIP contains:
  - `manifest.json` (metadata)
  - `institutions.csv`
  - `programs.csv`
  - `courses.csv`
  - `users.csv`
  - `terms.csv`
  - `course_offerings.csv`
  - `course_sections.csv`
  - `course_outcomes.csv`
- ✅ **Headers Present**: Each CSV has proper column headers
- ✅ **Row Counts Match**: CSV row counts match database entity counts
- ✅ **Data Integrity**: Spot-check 5 random records against database

**Specific Validations**:

```bash
# After opening exported file, check:
# 1. Course numbers match database exactly (no truncation)
# 2. Course titles are complete (no cutoff at 255 chars)
# 3. Departments are consistent with imports
# 4. Credits are integers (not formatted as "3.0")
# 5. No encoding issues (special characters display correctly)
```

**Database vs. Export Comparison**:

```bash
# Count courses in database
python -c "
from database_service import get_all_courses
courses = get_all_courses() or []
print(f'Database courses: {len(courses)}')
print(f'Sample: {courses[0].get(\"course_number\")} - {courses[0].get(\"course_title\")}')
"
# Compare with export file row count (should match)
```

**Critical Assertions**:

- [ ] Export file contains 40-50 courses (matches import)
- [ ] All course numbers from import are present in export
- [ ] No empty rows or missing data
- [ ] Excel formulas are NOT present (raw data only)
- [ ] Can re-open file without errors

---

### **TC-IE-102: Export Data Security Validation**

**Purpose**: Verify Generic CSV export excludes sensitive data

**Prerequisites**: TC-IE-002 passed (data imported)

**Steps**:

1. Export via Generic CSV (from TC-IE-101)
2. Extract ZIP and open `users.csv`
3. Inspect CSV headers and data

**Expected Results - Security**:

- ✅ **No Password Hashes**: `password_hash` column NOT present in users.csv
- ✅ **No Active Tokens**: `password_reset_token`, `email_verification_token` NOT present
- ✅ **User Data Present**: `email`, `first_name`, `last_name`, `role` columns present
- ✅ **Account Status**: `account_status` indicates "imported" or "pending"
- ✅ **Email Validity**: All emails are valid format
- ✅ **Security Note**: manifest.json explains security exclusions

**Specific Validations**:

- [ ] Instructor emails match import data
- [ ] All roles are "instructor" (lowercase)
- [ ] No duplicate emails
- [ ] Account statuses are "imported" or "active"
- [ ] Department field populated (if available from import)

**Critical Assertions**:

- [ ] Export contains 15-20 users
- [ ] No personal sensitive data exposed (passwords, tokens)
- [ ] Email format valid for all rows
- [ ] Can use exported file as reference for validation

---

### **TC-IE-103: Export Referential Integrity Validation**

**Purpose**: Verify Generic CSV export maintains proper foreign key relationships

**Prerequisites**: TC-IE-002 passed (data imported)

**Steps**:

1. Export via Generic CSV (from TC-IE-101)
2. Extract ZIP and parse multiple CSVs
3. Validate foreign key relationships across CSVs

**Expected Results - Referential Integrity**:

- ✅ **Programs → Institutions**: All `institution_id` in programs.csv exist in institutions.csv
- ✅ **Courses → Institutions**: All `institution_id` in courses.csv exist in institutions.csv
- ✅ **Sections → Courses**: All `course_id` in course_sections.csv exist in courses.csv
- ✅ **Sections → Instructors**: All `instructor_id` in course_sections.csv exist in users.csv
- ✅ **Sections → Terms**: All `term_id` in course_sections.csv exist in terms.csv
- ✅ **Outcomes → Courses**: All `course_id` in course_outcomes.csv exist in courses.csv
- ✅ **No Orphans**: No records reference non-existent foreign keys

**Specific Validations**:

```bash
# Spot-check 3 sections:
# 1. Course number matches a real course
# 2. Instructor email matches a real user
# 3. Term name is valid format (FA2024)
# 4. Section number is sequential (001, 002, 003)
# 5. Enrollment is reasonable (0-50)
```

**Critical Assertions**:

- [ ] Export contains 60-80 sections
- [ ] No orphaned sections (invalid course_id references)
- [ ] Section numbers NOT UUIDs
- [ ] Enrollment counts are integers
- [ ] Status is "active" or "Active"

---

### **TC-IE-104: Roundtrip Validation (Export → Import → Compare)**

**Purpose**: Validate Generic CSV exported data can be re-imported without loss (bidirectional adapter test)

**Prerequisites**: TC-IE-101 passed (data exported)

**Steps**:

1. Take exported ZIP from TC-IE-101
2. **Backup database**: `cp course_records.db course_records_roundtrip.db`
3. Clear database: `python scripts/seed_db.py --clear`
4. Navigate to "Data Management" panel
5. Upload the **exported ZIP file**
6. Adapter: Auto-detected "Generic CSV Format (ZIP)"
7. Conflict Strategy: "Use theirs" (no conflicts expected on empty DB)
8. Click **"Import"**
9. Compare database state to original

**Expected Results - Roundtrip Success**:

- ✅ **Import Succeeds**: No errors parsing exported ZIP
- ✅ **Data Integrity**: All entities present after re-import
- ✅ **No Data Loss**: All details unchanged (names, IDs, relationships)
- ✅ **Foreign Keys Valid**: All relationships maintained
- ✅ **Count Match**: Entity counts match pre-export counts
- ✅ **Bidirectional Proof**: Successful roundtrip proves bidirectional adapter works

**Database Comparison**:

```bash
python -c "
from database_service import get_all_courses
courses = get_all_courses() or []
print(f'Post-roundtrip courses: {len(courses)}')
# Should match pre-export count exactly
"
```

**Critical Assertions**:

- [ ] Course count unchanged after roundtrip
- [ ] Spot-check 5 courses - data unchanged
- [ ] No new orphaned records
- [ ] Export format is import-compatible

---

## 🔁 SCENARIO 3: (DEFERRED) Multi-Format Export

**Note**: Currently YAGNI (You Ain't Gonna Need It) - Generic CSV (ZIP) is sufficient as the universal bidirectional format.

Future export formats (Excel, JSON, individual CSVs) deferred until customer demand justifies implementation.

---

## 📊 Test Execution Checklist

### Pre-Test Setup

- [ ] Database backup created
- [ ] Server running and healthy (`/api/health` returns 200)
- [ ] Browser console clear (no pre-existing errors)
- [ ] Test data file accessible: `research/MockU/2024FA_test_data.xlsx`

### During Testing

- [ ] Browser console open (F12) to catch JavaScript errors
- [ ] Network tab monitoring for HTTP errors
- [ ] Screenshot any unexpected behavior
- [ ] Note exact error messages (don't paraphrase)
- [ ] Record timestamps for performance issues

### Post-Test Validation

- [ ] Database restored if needed: `cp course_records_roundtrip.db course_records.db`
- [ ] Verify no orphaned records: `python scripts/validate_referential_integrity.py` (if exists)
- [ ] Clear browser cache if testing UI changes

---

## 🚨 Known Limitations & Edge Cases

### Current Limitations

- **Adapters**: Two adapters available
  - **Generic CSV** (`generic_csv_v1`): Bidirectional ZIP format, institution-agnostic, **primary adapter for UAT**
  - **MockU Excel** (`cei_excel_format_v1`): Customer-specific, import-only, not covered in UAT
- **Single Institution Import**: Multi-institution imports not yet supported
- **No Partial Updates**: Cannot update individual fields without full record
- **Section Numbers**: Auto-generated as sequential (001, 002) - not preserved from import
- **Instructor Assignment**: Requires valid email in import file

### Edge Cases to Test Manually

1. **Empty Cells in Excel**: How does import handle missing course titles?
2. **Special Characters**: Test with course names like "C++ Programming"
3. **Large Files**: Test with 500+ rows (performance validation)
4. **Concurrent Imports**: Two users importing simultaneously (not covered here)

---

## 🐛 Bug Report Template

### When You Find a Bug

**Title**: [Import/Export] Brief description

**Severity**: Critical / High / Medium / Low

**Test Case**: TC-IE-XXX

**Steps to Reproduce**:

1. ...
2. ...

**Expected Result**:

- What should happen

**Actual Result**:

- What actually happened
- Screenshot attached

**Environment**:

- Browser: Chrome 120.0
- OS: macOS 14.5
- Test File: 2024FA_test_data.xlsx
- Database: SQLite (fresh install)

**Additional Notes**:

- JavaScript console errors (if any)
- Network tab HTTP status codes
- Database state after bug (query results)

---

## ✅ Success Criteria

### Import System Ready for Production

- [ ] All import test cases (TC-IE-001 to TC-IE-008) pass
- [ ] Dry run validation works correctly
- [ ] Conflict resolution prevents duplicates
- [ ] Error messages are actionable
- [ ] All entity relationships intact (courses→sections→instructors→terms)

### Export System Ready for Production

- [ ] All export test cases (TC-IE-101 to TC-IE-202) pass
- [ ] All formats (Excel, CSV, JSON) work
- [ ] Exported data matches database exactly
- [ ] Roundtrip validation passes (import→export→import)
- [ ] No sensitive data exposed in exports

### Overall System Health

- [ ] No JavaScript errors during any workflow
- [ ] No HTTP 500 errors (all errors handled gracefully)
- [ ] Database referential integrity maintained
- [ ] UI is responsive and intuitive
- [ ] Performance acceptable (< 10 seconds for most operations)

---

_This UAT guide is designed to catch real-world bugs that automated tests miss. Update this document as new edge cases are discovered._
