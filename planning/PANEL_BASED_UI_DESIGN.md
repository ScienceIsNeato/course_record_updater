# Panel-Based UI Design - Role-Specific Dashboard Layouts

## **Design Philosophy**
- **Workflow-centered panels**: Each panel serves a specific task or information need
- **Collapsible sections**: Users control information density
- **Tabular data presentation**: Familiar spreadsheet-like interface
- **Role-based filtering**: Data automatically filtered by user's oversight authority
- **Contextual actions**: Actions available directly within relevant panels

---

## **1. SITE ADMIN Dashboard**
**Role**: System-wide oversight and configuration
**Authority**: All institutions, programs, courses, and users

### **Header Section**
```
🏛️ Site Administration | System-wide oversight and configuration
Current Term: Fall 2024 | [3 Institutions] | [8 Programs] | [12 Courses] | [15 Users]
```

**Interactive Header Stats**: Click any bracketed number to see inline preview:
- **[3 Institutions]** → Shows mini-table: CEI, RCC, PTU with user counts
- **[8 Programs]** → Shows mini-table: All programs across institutions
- **[12 Courses]** → Shows mini-table: All courses with enrollment
- **[15 Users]** → Shows mini-table: Recent users with roles

### **Panel Layout**

#### **Panel 1: Institution Overview** `[▼]`
**Purpose**: Monitor all institutions in the system
```
┌─ 🏛️ Institution Management ──────────────────────────── [▼] ─┐
│ Institution ↕              │ Users ↕ │ Programs ↕ │ Courses ↕ │ Status ↕ │
│ California Engineering Inst│   7     │    3       │    4      │ Active   │
│ Riverside Community College│   5     │    2       │    3      │ Active   │
│ Pacific Technical Univ     │   3     │    3       │    5      │ Active   │
│                           │ [Add Institution] [Settings]           │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 2: System Activity** `[▼]`
**Purpose**: Monitor recent system-wide activity
```
┌─ 📊 Recent System Activity ──────────────────────────── [▼] ─┐
│ Timestamp ↕ │ Institution ↕ │ User ↕        │ Action ↕         │ Details ↕ │
│ 2:34 PM     │ CEI           │ Sarah Johnson │ CLO Assessment   │ CS-101    │
│ 1:15 PM     │ RCC           │ Mike Admin    │ User Created     │ New Instr │
│ 11:30 AM    │ PTU           │ System        │ Term Created     │ Spr 2025  │
│ 10:45 AM    │ CEI           │ John Smith    │ CLO Completed    │ EE-101.2  │
│                                        │ [View All] [Filter]          │
└─────────────────────────────────────────────────────────────────────┘
```


#### **Panel 4: User Management** `[▼]`
**Purpose**: Manage users across all institutions
```
┌─ 👥 User Management ─────────────────────────────────── [▼] ─┐
│ Name ↕        │ Email ↕            │ Role ↕      │ Institution ↕ │ Status ↕ │
│ Sarah Johnson │ sarah.admin@cei.edu│ Inst Admin  │ CEI          │ Active   │
│ Lisa Wang     │ lisa.prog@cei.edu  │ Prog Admin  │ CEI          │ Active   │
│ Mike Admin    │ mike.admin@rcc.edu │ Inst Admin  │ RCC          │ Active   │
│ John Smith    │ john.instructor... │ Instructor  │ CEI          │ Active   │
│                              │ [Add User] [Bulk Import]       │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 5: Data Export** `[▲]`
**Purpose**: Export system data (scoped to all institutions)
```
┌─ 📄 Data Export ─────────────────────────────────────── [▲] ─┐
│ [Collapsed - click to expand]                                    │
│ • Quick Export: [All Users] [All Institutions] [System Activity] │
│ • Formats: CSV | Access | JSON             │
└──────────────────────────────────────────────────────────────────┘
```

---

## **2. INSTITUTION ADMIN Dashboard**
**Role**: Institution-wide management and oversight
**Authority**: Single institution, all programs and courses within institution

### **Header Section**
```
🏛️ Institution Administration | Manage programs and faculty and Outcomes
California Engineering Institute | [3 Programs] | [4 Courses] | [7 Faculty]
```

**Interactive Header Stats**: Click any bracketed number to see inline preview:
- **[3 Programs]** → Shows: CS (45 students), EE (32 students), Unclassified (15 students)
- **[4 Courses]** → Shows: CS-101, CS-201, EE-101, EE-201 with instructors
- **[7 Faculty]** → Shows: Faculty list with teaching assignments

### **Panel Layout**

#### **Panel 1: Programs** `[▼]`
**Purpose**: Manage programs within the institution
```
┌─ 📚 Program Management ──────────────────────────────── [▼] ─┐
│ Program ↕         │ Courses │ Faculty │ Students │ Progress │ Actions │
│ Computer Science  │    2    │    3    │    45    │   75%    │ [Manage] │
│ Electrical Eng    │    2    │    2    │    32    │   60%    │ [Manage] │
│ Unclassified     │    0    │    2    │    15    │   20%    │ [Manage] │
│                                │ [Add Program]                    │
└─────────────────────────────────────────────────────────────────┘
```

**Manage Actions Available:**
- Edit program details (name, description, requirements)
- Assign/remove faculty to program
- Manage course assignments within program
- Set program learning outcomes (PLOs)
- View detailed program statistics

#### **Panel 2: Faculty Overview** `[▼]`
**Purpose**: Monitor faculty and their course assignments
```
┌─ 👨‍🏫 Faculty Management ──────────────────────────────── [▼] ─┐
│ Faculty Name ↕ │ Program │ Courses │ Sections │ CLO Progress │ Role ↕    │
│ Lisa Wang      │ CS/EE   │    0    │    0     │     N/A      │ Admin     │
│ John Smith     │ CS      │    2    │    2     │    4/6       │ Instructor│
│ Jane Davis     │ EE      │    2    │    2     │    3/6       │ Instructor│
│ Dr. Chen       │ CS      │    1    │    2     │    4/4       │ Instructor│
│                        │ [Add Faculty] [Send Reminders]          │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 3: Course Sections** `[▼]`
**Purpose**: Monitor all course sections in the institution
```
┌─ 📖 Course Sections (Fall 2024) ──────────────────────── [▼] ─┐
│ Course ↕ │ Section │ Faculty Name ↕ │ Enrolled Students ↕ │ CLO Assessments ↕ │
│ CS-101   │   001   │ Dr. Chen       │        23           │     4/4 Subm      │
│ CS-101   │   002   │ Dr. Chen       │        20           │     4/4 Subm      │
│ CS-201   │   001   │ John Smith     │        19           │     2/4 Subm      │
│ EE-101   │   001   │ Jane Davis     │        15           │     3/3 Subm      │
│ EE-201   │   001   │ Jane Davis     │        17           │     1/3 Subm      │
│                            │ [Add Section] [Bulk Actions]         │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 4: Assessment Progress** `[▼]`
**Purpose**: Track CLO assessment completion across institution
```
┌─ 📊 Assessment Progress ─────────────────────────────── [▼] ─┐
│ Course ↕ │ Faculty Name ↕ │ CLOs │ Complete ↕ │ Due Date ↕ │ Status ↕   │
│ CS-101   │ Dr. Chen       │  4   │   4/4      │ Dec 1      │ ✅ Done    │
│ CS-201   │ John Smith     │  4   │   2/4      │ Dec 1      │ ⚠️ Partial │
│ EE-101   │ Jane Davis     │  3   │   3/3      │ Dec 1      │ ✅ Done    │
│ EE-201   │ Jane Davis     │  3   │   1/3      │ Dec 1      │ ❌ Behind  │
│                              │ [Send Reminders]                    │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 5: Data Export** `[▲]`
**Purpose**: Export institution data (scoped to California Engineering Institute)
```
┌─ 📄 Data Export ─────────────────────────────────────── [▲] ─┐
│ [Collapsed - click to expand]                                    │
│ • Quick Export: [Programs] [Faculty] [Courses] [Assessments]    │
│ • Formats: CSV | Access | JSON             │
└──────────────────────────────────────────────────────────────────┘
```

---

## **3. PROGRAM ADMIN Dashboard**
**Role**: Program-specific management and oversight
**Authority**: Single program, courses and faculty within that program

### **Header Section**
```
📚 Program Administration | Manage curriculum and assessments
Computer Science Program | [2 Courses] | [3 Faculty] | [45 Students]
```

**Interactive Header Stats**: Click any bracketed number to see inline preview:
- **[2 Courses]** → Shows: CS-101 (Dr. Chen), CS-201 (John Smith)
- **[3 Faculty]** → Shows: Dr. Chen, John Smith, Lisa Wang (admin)
- **[45 Students]** → Shows: Enrollment breakdown by course

### **Panel Layout**

#### **Panel 1: Courses** `[▼]`
**Purpose**: Manage courses within the program
```
┌─ 📖 Course Management ───────────────────────────────── [▼] ─┐
│ Course ↕ │ Title ↕               │ Faculty Name ↕ │ Sections │ Students │ CLOs │
│ CS-101   │ Intro to Programming  │ Dr. Chen       │    2     │    23    │  4   │
│ CS-201   │ Data Structures       │ John Smith     │    1     │    19    │  4   │
│                                │ [Add Course] [Edit CLOs]           │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 2: Faculty Assignments** `[▼]`
**Purpose**: Manage faculty teaching assignments
```
┌─ 👨‍🏫 Faculty Assignments ──────────────────────────────── [▼] ─┐
│ Name        │ Courses │ Sections │ Students │ CLO Progress │ Status  │
│ Dr. Chen    │ CS-101  │    2     │    23    │     4/4      │ ✅ Done │
│ John Smith  │ CS-201  │    1     │    19    │     2/4      │ ⚠️ Part │
│                              │ [Assign Courses] [Send Reminders] │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 3: CLO Management** `[▼]`
**Purpose**: Manage Course Learning Outcomes for the program
```
┌─ 🎯 Course Learning Outcomes ────────────────────────── [▼] ─┐
│ Course  │ CLO ID  │ Description                    │ Status │ Actions │
│ CS-101  │ CS101.1 │ Write basic Python programs    │ Active │ [Edit]  │
│ CS-101  │ CS101.2 │ Debug code effectively         │ Active │ [Edit]  │
│ CS-201  │ CS201.1 │ Implement data structures      │ Active │ [Edit]  │
│ CS-201  │ CS201.2 │ Analyze algorithm complexity   │ Active │ [Edit]  │
│                                    │ [Add CLO] [Bulk Edit] [Export] │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 4: Assessment Results** `[▼]`
**Purpose**: Review assessment results for program courses
```
┌─ 📊 Assessment Results ──────────────────────────────── [▼] ─┐
│ Course  │ CLO     │ Students │ Passed │ Rate │ Result │ Trend │
│ CS-101  │ CS101.1 │    23    │   20   │ 87%  │   S    │  ↗️   │
│ CS-101  │ CS101.2 │    23    │   18   │ 78%  │   S    │  ↗️   │
│ CS-201  │ CS201.1 │    19    │   15   │ 79%  │   S    │  ↘️   │
│ CS-201  │ CS201.2 │    19    │   12   │ 63%  │   U    │  ↘️   │
│                                    │ [Detailed View]                  │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 5: Data Export** `[▲]`
**Purpose**: Export program data (scoped to Computer Science Program)
```
┌─ 📄 Data Export ─────────────────────────────────────── [▲] ─┐
│ [Collapsed - click to expand]                                    │
│ • Quick Export: [Courses] [CLOs] [Faculty] [Assessment Results] │
│ • Formats: CSV | Access | JSON             │
└──────────────────────────────────────────────────────────────────┘
```

---

## **4. INSTRUCTOR Dashboard**
**Role**: Course instruction and assessment completion
**Authority**: Only courses they are assigned to teach

### **Header Section**
```
👨‍🏫 Instructor Dashboard | Complete course assessments
John Smith | [2 Courses] | [3 Sections] | [42 Students] | [2/8 CLOs Complete]
```

**Interactive Header Stats**: Click any bracketed item to see inline preview:
- **[2 Courses]** → Shows: CS-101, CS-201 with schedules
- **[3 Sections]** → Shows: Section details with room/time
- **[42 Students]** → Shows: Enrollment by section
- **[2/8 CLOs Complete]** → Shows: Which CLOs are pending

### **Panel Layout**

#### **Panel 1: Teaching Assignment** `[▼]`
**Purpose**: View assigned courses and sections
```
┌─ 📚 Teaching Assignment ─────────────────────────────── [▼] ─┐
│ Course ↕ │ Title ↕          │ Section │ Students │ Schedule      │ Room   │
│ CS-101   │ Intro Programming│   001   │    23    │ MWF 9:00-9:50 │ ENG101 │
│ CS-201   │ Data Structures  │   001   │    19    │ TTh 2:00-3:15 │ ENG201 │
│                                          │ [View Roster] [Gradebook] │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 2: Assessment Tasks** `[▼]`
**Purpose**: Track CLO assessment completion status
```
┌─ ⏰ Assessment Tasks ─────────────────────────────────── [▼] ─┐
│ Course  │ CLO Description              │ Due Date │ Status     │ Action  │
│ CS-101  │ Write basic Python programs  │ Dec 1    │ ✅ Done    │ [View]  │
│ CS-101  │ Debug code effectively       │ Dec 1    │ ✅ Done    │ [View]  │
│ CS-101  │ Use data structures          │ Dec 1    │ ✅ Done    │ [View]  │
│ CS-101  │ Apply problem-solving        │ Dec 1    │ ✅ Done    │ [View]  │
│ CS-201  │ Implement data structures    │ Dec 1    │ ❌ Missing │ [Enter] │
│ CS-201  │ Analyze algorithms           │ Dec 1    │ ❌ Missing │ [Enter] │
│ CS-201  │ Design efficient solutions   │ Dec 1    │ ⚠️ Draft   │ [Edit]  │
│ CS-201  │ Evaluate complexity          │ Dec 1    │ ❌ Missing │ [Enter] │
│                                                │ [Bulk Enter] [Export] │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 3: Recent Activity** `[▲]`
**Purpose**: Show recent assessment work (collapsed by default)
```
┌─ 📝 Recent Activity ─────────────────────────────────── [▲] ─┐
│ [Collapsed - click to expand]                                │
│ • CS-101.4 completed 2 hours ago • CS-201.3 saved as draft  │
└─────────────────────────────────────────────────────────────┘
```

#### **Panel 4: Quick Course Summary** `[▼]`
**Purpose**: Overview of course enrollment and basic stats
```
┌─ 📊 Course Summary ──────────────────────────────────── [▼] ─┐
│ Course  │ Enrolled │ Withdrew │ Passed │ D/C/I │ Pass Rate │
│ CS-101  │    23    │    1     │   20   │   2   │    87%    │
│ CS-201  │    19    │    0     │   15   │   4   │    79%    │
│                                              │ [Update] [Details] │
└─────────────────────────────────────────────────────────────────┘
```

#### **Panel 5: Data Export** `[▲]`
**Purpose**: Export course data (scoped to assigned courses only)
```
┌─ 📄 Data Export ─────────────────────────────────────── [▲] ─┐
│ [Collapsed - click to expand]                                    │
│ • Quick Export: [Assessment Tasks] [Course Summary] [Rosters]   │
│ • Formats: CSV | Access | JSON             │
└──────────────────────────────────────────────────────────────────┘
```

---

## **Shared Panel Concepts**

### **Panel States**
- **Expanded** `[▼]`: Full content visible
- **Collapsed** `[▲]`: Header only with summary info
- **Loading** `[⟳]`: Data being fetched
- **Error** `[⚠️]`: Problem loading data
- **Sortable** `↕`: Column can be sorted by clicking header

### **Data Filtering Rules**
- **Site Admin**: Sees all data across all institutions
- **Institution Admin**: Sees only data for their institution
- **Program Admin**: Sees only data for their program(s)
- **Instructor**: Sees only data for courses they teach

### **Common Actions**
- **Export**: Download data as Excel/CSV
- **Filter**: Search and filter table data
- **Sort**: Click column headers to sort (↕ indicates sortable columns)
- **Expand/Collapse**: Control panel visibility
- **Refresh**: Update panel data

### **Interactive Header Stats**
- **Bracketed Numbers**: Clickable stats in headers (e.g., [3 Programs]) show inline previews
- **Inline Expansion**: Clicking a stat temporarily expands a mini-table below the header
- **Quick Preview**: Shows 3-5 most relevant items without navigation
- **Auto-collapse**: Closes when clicking elsewhere or after 10 seconds
- **No Popup**: Avoids clunky modal dialogs - keeps context in place

### **Panel Focus Navigation**
- **Clickable Panel Titles**: Click any panel title (e.g., "Programs") to focus that panel as main view
- **Full-Screen Panel**: Focused panel expands to use full dashboard area
- **Breadcrumb Navigation**: Shows "Dashboard > Programs" with clickable path back
- **Quick Actions**: Focused view shows all actions/filters for that data type
- **Return to Dashboard**: Breadcrumb "Dashboard" link returns to multi-panel view

### **Data Definitions**
- **CLO Assessments**: Fraction showing submitted CLO assessments out of total (e.g., "4/4 Subm" = all 4 CLO assessments submitted by instructor)
- **CLO Progress**: Same as CLO Assessments - tracks instructor submission status, not student performance
- **Enrolled Students**: Total students registered for the course (from Excel `Enrolled Students`)
- **Faculty Name**: Instructor name (from Excel `Faculty Name`)
- **Status**: Assessment submission status (Done = all CLOs submitted, Partial = some submitted, Behind = overdue)

### **Responsive Design**
- **Desktop**: All panels side-by-side or stacked
- **Tablet**: Panels stack vertically
- **Mobile**: Single column, collapsible by default

---

## **Implementation Notes**

### **Panel Component Structure**
```javascript
<Panel title="My Courses" icon="📚" collapsible={true} defaultExpanded={true}>
  <PanelHeader>
    <PanelTitle>My Courses</PanelTitle>
    <PanelActions>
      <Button>Add Course</Button>
      <Button>Export</Button>
    </PanelActions>
  </PanelHeader>
  <PanelContent>
    <DataTable data={courses} columns={courseColumns} />
  </PanelContent>
</Panel>
```

### **Data Loading Strategy**
- **Lazy loading**: Panels load data when expanded
- **Real-time updates**: WebSocket or polling for live data
- **Caching**: Cache panel data to reduce API calls
- **Pagination**: Handle large datasets efficiently

### **User Preferences**
- **Panel layout**: Remember expanded/collapsed state
- **Column visibility**: Hide/show table columns
- **Sort preferences**: Remember sort order
- **Refresh intervals**: Configurable auto-refresh

This design provides a clear roadmap for implementing the panel-based UI that matches your SITE_MAP vision while serving each user role's specific needs and workflows.
