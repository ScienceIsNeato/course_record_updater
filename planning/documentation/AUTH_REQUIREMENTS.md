# Authentication & Authorization Requirements

## User Roles & Permissions

### 1. SITE_ADMIN (Global)
**Who:** Site owner/developer
**Scope:** All institutions and programs, all data
**Abilities:**
- Full CRUD access to all institutions, programs, and courses
- User management across all levels
- System configuration and maintenance
- Billing/subscription management oversight
- Analytics and reporting across all tenants

### 2. MULTI_PROGRAM_ADMINISTRATOR
**Who:** Manages multiple programs within an institution (e.g., department head overseeing Biology, Chemistry, Physics)
**Scope:** Only the programs they are explicitly assigned to + all courses within those programs
**Pricing:** $39.99/month + $X * 0.75 per course
**Abilities:**
- **Program Management:** Create/edit programs they manage (not institution-wide)
- **User Management:**
  - Invite Program Administrators to their programs
  - Invite Regular Users to their programs
  - Manage access only within their assigned programs
- **Course Management:** Full CRUD on courses within their assigned programs only
- **Data Views:** Access live views across their assigned programs with export capabilities
- **Account Management:** Manage billing and settings for their programs

### 3. PROGRAM_ADMINISTRATOR
**Who:** Manages a single academic program/department
**Scope:** One program + all courses within that program
**Pricing:** $19.99/month + $X per course
**Abilities:**
- **Program Management:** Edit their single program settings
- **User Management:**
  - Invite Regular Users to their program
  - Manage faculty assignments within their program
- **Course Management:** Full CRUD on courses within their program
- **Data Views:** Access live views for their program with export capabilities
- **Account Management:** Manage their program's billing and settings

### 4. REGULAR_USER
**Who:** Faculty, teaching assistants, program staff
**Scope:** Courses they have access to within their assigned program(s)
**Pricing:** Free
**Multi-Institution Support:** Users can belong to multiple institutions with separate access controls
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
