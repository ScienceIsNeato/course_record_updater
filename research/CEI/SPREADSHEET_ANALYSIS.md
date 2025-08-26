# CEI Spreadsheet Deep Dive Analysis

## 📊 Data Structure Overview

### File Details
- **Filename:** `2024FAresults.xlsx`
- **Main Sheet:** `qry_2024FA_cllos_informer` (1,543 rows × 18 columns)
- **Other Sheets:** "ugly but functional form" & "relationships" (empty - likely screenshots)
- **Term:** 2024FA (Fall 2024)

### Data Scale
- **173 unique courses** across all programs
- **312 unique course-instructor combinations** 
- **145 unique faculty members**
- **1,543 CLO records** (multiple CLOs per course)

## 🏗️ Data Model Revealed

### Hierarchical Structure
```
Institution (CEI)
├── Programs (implied by course prefixes: ACC, ENGL, MATH, BIOL, etc.)
├── Courses (173 unique: ACC-201, ENGL-101, MATH-143, etc.)
├── Course Instances (312: Course + Instructor combinations)
└── CLOs (1,543: Multiple per course instance)
```

### Key Entity: Course Learning Outcomes (CLOs)

**Each CLO Record Contains:**
- **Course Info:** Course code, instructor, term
- **Enrollment Data:** Total enrolled, withdrawals
- **Course-Level Results:** Students passed, D/C/Incomplete
- **CLO-Specific Data:** Assessment results, pass rates, narratives

## 📋 Complete Field Mapping

### 1. Course Identification
- **`course`** → Our `course_number` (e.g., "ACC-201")
- **`combo`** → Course + Instructor (e.g., "ACC-201:Abbigail Stauffer")
- **`Faculty Name`** → Our `instructor_name`
- **`Term`** → Our `semester` ("2024FA")

### 2. Enrollment Data (Course-Level)
- **`Enrolled Students`** → Our `total_students`
- **`Total W's`** → Our `students_withdrew`
- **`pass_course`** → Our `students_passed_course`
- **`dci_course`** → Our `students_dc_incomplete`

### 3. CLO Assessment Data (New Entity Needed!)
- **`cllo_text`** → CLO description (e.g., "ACC-201.1: Complete the accounting cycle...")
- **`passed_c`** → Students who passed this CLO assessment
- **`took_c`** → Students who took this CLO assessment  
- **`%`** → Pass rate percentage (passed_c ÷ took_c)
- **`result`** → S/U based on 75% threshold

### 4. Narrative Fields
- **`celebrations`** → What went well
- **`challenges`** → What was difficult
- **`changes`** → Planned improvements

### 5. System Fields
- **`effterm_c`** → Effective term (course catalog)
- **`endterm_c`** → End term (when course expires)

## 🎯 Critical Discovery: CLO-Centric Model

### What Leslie's Video + Spreadsheet Reveals:

**We need a NEW primary entity: Course Learning Outcome (CLO)**

```
CourseInstance (1) → CLOs (Many)
```

**Example from Data:**
- **Course:** ACC-201 (Abbigail Stauffer, Fall 2024)
- **Enrollment:** 14 students, 1 withdrawal
- **CLOs:** 3 different learning outcomes
  1. "Complete the accounting cycle using double entry framework"
  2. "Work effectively in team setting for accounting cycle" 
  3. "Demonstrate Excel spreadsheets in accounting transactions"

### CLO Assessment Process:
1. **Course-level data** entered once (enrollment, withdrawals, overall pass/fail)
2. **Each CLO assessed separately** with specific assessment tools
3. **CLO pass rates calculated** (students passed ÷ students took)
4. **S/U determination** based on 75% threshold
5. **Narrative feedback** for each CLO

## 📈 Data Patterns & Insights

### Course Distribution
**Most CLO-heavy courses:**
- ENGL-101: 77 CLO records
- ENGL-102: 49 CLO records  
- HCT-101: 40 CLO records
- PSYC-101: 36 CLO records

### Faculty Workload
**Faculty teaching most courses:**
- Cathy Owen: 7 different courses
- Matthew Janes: 6 courses
- Blake Beck: 6 courses
- Abbigail Stauffer: 6 courses

### CLO Naming Convention
**Pattern:** `COURSE-###.#: Description`
- ACC-201.1: Complete the accounting cycle...
- ACC-201.2: Work effectively in team setting...
- ANTH-102.1: Understand basic components...

## 🚨 Current System Problems (From Video)

### Technical Issues
1. **Microsoft Access limitations** - "bubble gum and duct tape"
2. **Row locking problems** - multi-user concurrency failures
3. **Data integrity issues** - records go to wrong rows
4. **Poor form UX** - "I can't build forms, but it's functional"

### Process Pain Points
1. **Manual data reconciliation** - math doesn't always add up
2. **Export/import cycle** - Access → Excel → back to Access
3. **Faculty data collection** - need better forms for instructors
4. **Reporting complexity** - hard to generate clean reports

## 🎯 Our Solution Validation

### Perfect Problem-Solution Fit ✅

**Their Problems → Our Solutions:**
- **Multi-user issues** → Web-based concurrent access
- **Poor forms** → Modern, intuitive web UI
- **Data integrity** → Proper relational database with constraints  
- **Export/import cycle** → Real-time web application
- **Manual calculations** → Automatic pass rate calculations
- **Access limitations** → Scalable cloud architecture

### Migration Strategy
**Option 1:** Direct Access DB export → Firestore import
**Option 2:** Use spreadsheet as data source (cleaner)
**Recommendation:** Spreadsheet import - data is already structured

## 📊 Updated Data Model Requirements

### New Primary Entity: CourseOutcome (CLO)
```sql
CourseOutcome:
- course_outcome_id (UUID)
- course_instance_id (foreign key)
- clo_number (e.g., "1", "2", "3")
- clo_description (full text)
- assessment_tool (how it was measured)
- students_took_assessment (integer)
- students_passed_assessment (integer)
- pass_rate_percentage (calculated)
- pass_threshold (default 75%)
- result_status (S/U based on threshold)
- celebrations (text)
- challenges (text)  
- changes (text)
```

### Enhanced CourseInstance Entity:
```sql
CourseInstance:
- total_students (enrollment)
- students_withdrew (W grades)
- students_passed_course (overall course pass)
- students_dc_incomplete (D/C/Incomplete grades)
- course_pass_rate (calculated)
- data_reconciled (boolean - math checks out)
```

## 🎯 Meeting Strategy

### Lead with Pain Point Solutions:
1. **"No more Access row locking issues"**
2. **"Professional forms that faculty will actually want to use"**
3. **"Automatic calculations - no more manual math reconciliation"**
4. **"All your existing data imported seamlessly"**

### Demo Data Understanding:
- **Show we understand their CLO-centric model**
- **Reference specific courses from their data (ACC-201, ENGL-101)**
- **Mention the 75% S/U threshold**
- **Acknowledge the celebration/challenges/changes workflow**

This analysis confirms our solution is EXACTLY what they need! 🎯
