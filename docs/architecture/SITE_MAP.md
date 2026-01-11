# LoopCloser - Site Map & URL Structure

## **Design Philosophy**
- **Workflow-centered navigation**: Pages follow Leslie's actual assessment workflow
- **Role-based access control**: Permissions handled by app logic, not URLs
- **Clear homepage**: Landing page guides users to their next logical action
- **Mobile-responsive**: All pages work on tablets/phones

---

## **URL Structure (No Role Prefixes)**

### **Core Workflow URLs**:
- `/` - Homepage/Dashboard (workflow-oriented landing)
- `/data/` - Data management and validation
- `/assessments/` - Monitor and manage assessment progress  
- `/quality/` - Audit and approve submissions
- `/export/` - Generate and download results
- `/settings/` - System configuration

---

## **Homepage/Dashboard (`/`)**
**Purpose**: Workflow-oriented landing page that guides users to their next action
**User Stories**: #2 (View Main Dashboard)

### **Smart Workflow Guidance**:
The homepage adapts based on current assessment workflow state:

#### **Typical Scenario: System Pre-loaded by Will**
- **Primary Focus**: Assessment progress overview
- **Key Metrics**: X course-instructor combinations ready, completion status
- **Primary Action**: "Send Invitations" or "Monitor Progress" (based on invitation status)
- **Quick Preview**: Recent activity, overdue submissions
- **Secondary Action**: "Manage Data" (if corrections needed)

#### **Scenario 1: Invitations Not Yet Sent**
- **Primary Action**: "Review & Send Invitations" 
- **Status Summary**: X courses loaded, Y instructors identified
- **Quick Actions**: Spot check sample assessments, send bulk invitations
- **Data Health**: Feed validation summary, any data issues

#### **Scenario 2: Assessment Period Active**
- **Primary Focus**: Real-time progress dashboard
- **Key Metrics**: Completion rates, overdue submissions, recent activity
- **Quick Actions**: Send reminders, review completed assessments
- **Trending Data**: Daily completion rates, instructor engagement

#### **Scenario 3: Assessment Period Complete**
- **Primary Action**: "Quality Review & Export"
- **Status Summary**: Quality check progress, export readiness
- **Final Steps**: Audit remaining submissions, export data

#### **Scenario 4: Mid-Semester Data Updates**
- **Primary Action**: "Update Course Data"
- **Warning Indicators**: Impact on existing submissions
- **Merge Strategy**: Options for handling data conflicts

### **Always Available Navigation**:
- **Data Management** - Upload and manage course data
- **Assessment Progress** - Monitor submissions
- **Quality Review** - Audit completed work
- **Export Results** - Download final data
- **System Settings** - Configure courses, CLOs, etc.

---

## **1. Data Management (`/data/`)**
**Workflow Step**: Manage course and assessment data during semester (system typically pre-loaded by Will)

### **Data Update & Validation (`/data/`)**
**Purpose**: Update existing course and assessment data with corrections or additions
**User Stories**: #1 (Upload Assessment Feed), #10 (Spot Check Data)

**Primary Use Cases**:
- **Mid-semester corrections**: Fix instructor assignments, course data, CLLO text
- **Additional courses**: Add late-added courses or sections
- **Data reconciliation**: Resolve enrollment or instructor conflicts

**Workflow on One Page**:
1. **Current Data Summary**: Overview of existing course-instructor combinations
2. **Upload Section**: File upload interface (.xlsx/.csv) for updates
3. **Impact Analysis**: Show what will change, what's affected
4. **Conflict Resolution**: Handle existing submissions vs. new data
5. **Validation Section**: Preview changes, check for errors
6. **Spot Check Section**: View updated course-instructor combinations
7. **Update Decision**: Confirm or reject changes after review

**Features**:
- Current data overview with search/filter
- Drag-and-drop file upload for updates
- **Change impact analysis**: Shows affected submissions
- **Merge strategies**: Replace, append, or merge with existing data
- Real-time validation with error highlighting
- Sample assessment form preview (spot check)
- Update progress indicator
- Full audit trail and rollback options
- **Submission protection**: Warn about overwriting completed assessments

---

## **2. Assessment Progress (`/assessments/`)**
**Workflow Step**: Monitor submissions, send invitations/reminders, manage instructor workflow

### **Main Assessment Dashboard (`/assessments/`)**
**Purpose**: Central hub for monitoring all assessment activity
**User Stories**: #2 (Main Dashboard), #6 (Send Invitations), #9 (Send Reminders)

**Key Sections on One Page**:
1. **Status Overview**: Progress charts, completion rates, overdue count
2. **Quick Actions**: Send invitations, send reminders, bulk operations
3. **Assessment List**: Filterable table of all course-instructor combinations
4. **Recent Activity**: Latest submissions, instructor logins, etc.

**Features**:
- Real-time status indicators (Assigned, Editing, Complete, Overdue)
- Bulk invitation sending with preview
- Bulk reminder sending to incomplete assessments
- Search and filter by course, instructor, status, term
- Export progress reports
- Direct links to individual assessments

### **Individual Assessment View (`/assessments/{combo_id}/`)**
**Purpose**: View specific course-instructor assessment (as instructor sees it)
**User Stories**: #10 (Access as Instructor), #25 (Edit as Admin)

**Features**:
- Read-only view matching instructor experience
- Admin edit mode for corrections
- Submission history and change tracking
- Communication log with instructor
- Quality audit notes

---

### **4. Quality Assurance**

#### **4.1 Review Queue (`/admin/quality/review/`)**
**Purpose**: Audit submitted assessments
**User Stories**: #11 (Quality Audit Process)

**Features**:
- Queue of submitted assessments
- Audit status checkboxes (imported, quality checked, remediate, NCI)
- Side-by-side comparison with original feed data
- Comments/notes for each submission
- Batch approval workflows

#### **4.2 Export Approval (`/admin/quality/approve/`)**
**Purpose**: Mark assessments ready for export
**User Stories**: #12 (Mark Ready for Export)

**Features**:
- List of quality-checked assessments
- Bulk "ready for export" marking
- Export batch creation
- Preview export data
- Export scheduling

#### **4.3 Export Management (`/admin/quality/export/`)**
**Purpose**: Generate and manage data exports
**User Stories**: #18-19 (Export and Clear Data)

**Features**:
- Create new export batches
- Download export files (.xlsx/.csv)
- Export history and status tracking
- Mark exports as "exported" 
- Clear exported data for new semester

---

### **5. Communication**

#### **5.1 Send Invitations (`/admin/communication/invitations/`)**
**Purpose**: Generate and send assessment invitations
**User Stories**: #6 (Generate and Send Invitations)

**Features**:
- Select course-instructor combinations
- Preview invitation emails
- Send individual or bulk invitations
- Track invitation status
- Resend failed invitations

#### **5.2 Send Reminders (`/admin/communication/reminders/`)**
**Purpose**: Send reminder messages to instructors
**User Stories**: #9 (Send Bulk Reminders)

**Features**:
- Filter incomplete assessments
- Select recipients for reminders
- Preview reminder messages
- Schedule reminder sending
- Track reminder effectiveness

#### **5.3 Message Templates (`/admin/communication/templates/`)**
**Purpose**: Manage email message templates
**User Stories**: #13-17 (Notification Management)

**Features**:
- Create/edit invitation templates
- Create/edit reminder templates
- Template variable management
- Preview templates with sample data
- Template usage analytics

---

### **6. System Settings**

#### **6.1 Course Management (`/admin/settings/courses/`)**
**Purpose**: Manage course templates and information
**User Stories**: #20-21 (Create Courses and Sections)

**Features**:
- Create new course templates
- Edit existing course information
- Manage course-CLO assignments
- Course catalog maintenance

#### **6.2 CLO Management (`/admin/settings/clos/`)**
**Purpose**: Manage Course Learning Outcomes library
**User Stories**: #23-24 (Manage and Assign CLOs)

**Features**:
- Create/edit CLO definitions
- Organize CLO library
- Assign CLOs to courses
- CLO usage reporting

#### **6.3 Term Management (`/admin/settings/terms/`)**
**Purpose**: Manage academic terms and calendars
**User Stories**: #22 (Manage Terms and Years)

**Features**:
- Create/edit academic terms
- Set term dates and deadlines
- Manage term transitions
- Archive old terms

---

## **Instructor Pages**

### **Assessment Form (`/assessment/{token}/`)**
**Purpose**: Complete course assessment (accessed via email link)
**User Stories**: All instructor stories (#1-18)

**Features**:
- Pre-populated course information
- Enrollment data entry with reconciliation check
- CLLO assessment data entry
- Auto-save functionality
- Narrative sections (celebrations, challenges, changes)
- Submit and confirmation
- PDF export of completed assessment

---

## **URL Structure Patterns**

### **RESTful Conventions**:
- `GET /admin/assignments/` - List all assignments
- `GET /admin/assignments/course/BIOL-228/` - Show specific course
- `POST /admin/assignments/course/BIOL-228/instructors/` - Add instructor to course
- `DELETE /admin/assignments/{combo_id}/` - Remove assignment

### **Consistent Navigation**:
- All admin pages under `/admin/` prefix
- Logical grouping by function
- Predictable URL patterns
- RESTful resource naming

### **Security Considerations**:
- Admin pages require authentication
- Assessment forms use secure tokens
- Role-based access control
- CSRF protection on all forms

---

## **Navigation Structure**

### **Primary Navigation** (Admin Header):
1. **Dashboard** - Overview and quick stats
2. **Feed** - Upload and validate data
3. **Assignments** - Manage course-instructor combinations
4. **Quality** - Audit and export workflow
5. **Communication** - Invitations and reminders
6. **Settings** - System configuration

### **Secondary Navigation** (Contextual):
- Breadcrumb navigation on all pages
- Related actions sidebar
- Quick filters and search
- "Back to list" links

---

## **Mobile Responsiveness**

### **Design Principles**:
- **Mobile-first CSS**: Start with mobile, enhance for desktop
- **Touch-friendly interface**: Large buttons, adequate spacing
- **Simplified navigation**: Collapsible menus, priority-based layout
- **Readable typography**: Appropriate font sizes, contrast ratios
- **Efficient data display**: Prioritize most important information

### **Page Adaptations**:
- **Tables**: Convert to card layouts on mobile
- **Forms**: Stack fields vertically, larger input areas
- **Navigation**: Hamburger menu, collapsible sections
- **Actions**: Primary actions prominent, secondary in menus

---

## **Implementation Priority**

### **Phase 1** (MVP):
1. Dashboard (`/admin/dashboard/`)
2. Feed Upload (`/admin/feed/upload/`)
3. Assignments Overview (`/admin/assignments/`)
4. Assessment Form (`/assessment/{token}/`)

### **Phase 2** (Core Workflow):
5. Quality Review (`/admin/quality/review/`)
6. Export Management (`/admin/quality/export/`)
7. Send Invitations (`/admin/communication/invitations/`)

### **Phase 3** (Full Features):
8. All remaining admin pages
9. Advanced communication features
10. Complete settings management

This structure provides a clear roadmap for development while ensuring the final product is production-ready rather than debug tooling.
