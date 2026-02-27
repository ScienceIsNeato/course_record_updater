# Authentication & Authorization Requirements

## User Roles & Permissions

### 1. SITE_ADMIN (Global)

**Who:** Site owner/developer
**Scope:** All institutions, programs, and courses across entire system
**Abilities:**

- Full CRUD access to all institutions, programs, and courses
- User management across all levels and institutions
- System configuration and maintenance
- Billing/subscription management oversight
- Analytics and reporting across all tenants
- Can impersonate any user for support purposes

### 2. INSTITUTION_ADMIN

**Who:** Manages an entire institution (college, university)
**Scope:** All programs and courses within their institution
**Pricing:** TBD based on institution size
**Abilities:**

- **Institution Management:** Edit institution settings and details
- **Program Management:** Create, edit, delete programs within their institution
- **User Management:**
  - Invite and manage Program Administrators
  - Invite and manage Instructors
  - Assign users to programs
  - Manage user roles within their institution
- **Course Management:** Full CRUD on all courses within their institution
- **Data Views:** Access institution-wide reports and analytics
- **Account Management:** Manage institution billing and settings

### 3. PROGRAM_ADMIN

**Who:** Manages one or more academic programs/departments
**Scope:** Only the programs they are explicitly assigned to + all courses within those programs
**Pricing:** TBD based on program size
**Abilities:**

- **Program Management:** Edit settings for their assigned programs only
- **User Management:**
  - Invite Instructors to their programs
  - Manage instructor assignments within their programs
  - Cannot create other Program Admins (only Institution Admin can)
- **Course Management:**
  - Full CRUD on courses within their assigned programs
  - Add/remove courses from their programs
  - Manage course-to-program associations
- **Data Views:** Access program-specific reports and analytics
- **Multi-Program:** Can be assigned to manage multiple programs

### 4. INSTRUCTOR

**Who:** Faculty, teaching assistants, program staff
**Scope:** Courses they have access to within their assigned program(s)
**Pricing:** Free
**Abilities:**

- **Course Data:** View and edit course data for assigned courses
- **Assessment Management:** Submit and manage course assessments
- **Reporting:** Access reports for their assigned courses
- **Profile Management:** Manage their own profile and preferences
  **Abilities:**
- **Data Entry:** Input course information via web forms
- **Course Management:** Create/edit courses they have access to
- **Data Views:** Access live views of their course data with export capabilities
- **Profile Management:** Update their own account settings
- **Institution Switching:** Toggle between institutions if they have multi-institutional access

## Multi-Institution Design Assumptions

### Core Assumption

**Users can work at multiple institutions** - Faculty commonly teach at multiple schools, so the system must support:

- Single user account with access to multiple institutions
- Clear data isolation between institutions
- Institution context switching in the UI
- Separate billing and permissions per institution

## Live Data Views Philosophy

### Core Approach

**Live data, not static reports** - All "reports" are live views of current data that can be exported at any time:

- Data is always current and reflects real-time state
- Users access live dashboards and views, not generated reports
- Export capabilities (PDF, Excel, CSV, Access) available from any view
- No "report generation" process - data views are always available
- Historical data maintained for trend analysis and comparisons

### Export Capabilities

- **PDF Export** - For formal submissions and printing
- **Excel Export** - For analysis and manipulation
- **CSV Export** - For integration with other systems
- **Access Export** - For legacy system compatibility
- **SQL Export** - For advanced users and migrations

## Data Entry Strategy

### Core Philosophy

**Simple, reliable web forms** - Provide intuitive forms that adapt to institutional needs.

### Primary Input Method

- **Web Forms** - Clean, responsive forms for all data entry
- **Dynamic Dropdowns** - Type-ahead fields that learn from existing data
- **Flexible Fields** - Institution-customizable form fields
- **Validation** - Real-time validation with helpful error messages
- **Auto-save** - Prevent data loss during long entry sessions

### Data Migration Support

- **One-time Import Service** - Professional data migration for new clients
- **Excel Import** - Simple spreadsheet upload for bulk course data
- **Manual Entry** - Always available as primary method
- **Export Tools** - Easy export to Excel, CSV, Access formats

### Form Customization

- **Institution-Level** - Admins can customize required/optional fields
- **Program-Level** - Program-specific field requirements
- **Field Types** - Text, number, dropdown, multi-select, date
- **Validation Rules** - Custom validation per institution needs

### Required Data Fields

**Core Fields:**

- Course number/identifier
- Semester/term
- Academic year
- Number of students
- Grade distribution (A, B, C, D, F percentages or counts)
- Instructor information
- Program/department affiliation

**Optional/Contextual Fields:**

- Learning outcomes assessment
- Pass/fail rates
- Withdrawal rates
- Course modality (online, in-person, hybrid)

## Authentication Implementation

### Primary Method: OAuth/Social Login

**Supported Providers:**

- Google (Gmail accounts)
- Microsoft (Outlook/Office 365)
- Apple ID
- Possibly: LinkedIn, Facebook

**Benefits:**

- Familiar user experience
- Reduces password fatigue
- Leverages existing security infrastructure
- Easier onboarding

### Fallback Method: Traditional Auth

**For users who prefer traditional login:**

- Email/username + password
- Password complexity requirements
- Optional 2FA via SMS/authenticator app
- Password reset via email

### Registration Flow

**Simple Dropdown Selection:** Any user can sign up and select their role:

1. **Institution Administrator:**
   - "I oversee multiple programs at an institution"
   - Creates institution profile during signup
   - Can immediately start creating programs

2. **Program Administrator:**
   - "I manage a single program/department"
   - Creates program profile during signup
   - Defaults to being their own administrator

3. **Regular User:**
   - "I input course data and need to join an existing program"
   - Free tier - can create courses immediately
   - Can be invited to programs later by administrators

## Data Isolation Strategy

### Hierarchical Architecture

- **Institution → Programs → Courses** hierarchy
- **Program ID** as primary tenant identifier for most operations
- All data records tagged with program_id and institution_id
- Users can only access data within their assigned programs
- API endpoints filter by user's program/institution context

### Session Management

- JWT tokens with institution context
- Role-based permissions encoded in token
- Automatic tenant filtering on all database queries
- Cross-institution access explicitly forbidden (except for SITE_ADMIN)

## Security Considerations

### Access Control

- Role-based permissions enforced at API level
- Frontend UI adapts based on user role
- Audit logging for all data modifications
- Rate limiting on API endpoints

### Data Protection

- Encryption at rest and in transit
- Regular security audits
- GDPR/FERPA compliance considerations
- Secure file upload handling for document processing

## Implementation Notes

### Technology Stack Considerations

- **OAuth Libraries:** NextAuth.js, Auth0, or Firebase Auth
- **Database:** PostgreSQL with RLS or MongoDB with tenant filtering
- **File Processing:** Cloud storage with basic security scanning

### Phase 1 (MVP) Scope

- Basic OAuth + traditional auth
- Simple role-based permissions
- Manual data entry forms
- Basic document upload and processing

### Phase 2 (Enhancement)

- Advanced permission granularity
- Audit logging and compliance features
- Advanced reporting and analytics
