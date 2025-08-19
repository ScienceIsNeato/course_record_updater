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

### 2. INSTITUTION_ADMINISTRATOR
**Who:** Oversees multiple programs within an institution
**Scope:** All programs they manage + all courses within those programs
**Pricing:** $39.99/month + $X * 0.75 per course
**Abilities:**
- **Program Management:** Create/edit/delete multiple programs
- **User Management:** 
  - Assign Program Administrators to programs
  - Invite Regular Users to any of their programs
  - Manage user roles across their programs
- **Course Management:** Full CRUD on courses across all their programs
- **Reporting:** Generate reports across all their programs
- **Account Management:** Manage billing, usage statistics, export data

### 3. PROGRAM_ADMINISTRATOR
**Who:** Manages a single academic program/department
**Scope:** One program + all courses within that program
**Pricing:** $19.99/month + $X per course
**Abilities:**
- **Program Management:** Edit their single program settings
- **User Management:**
  - Invite Regular Users to their program
  - Assign themselves as default administrator
- **Course Management:** Full CRUD on courses within their program
- **Reporting:** Generate reports for their program
- **Account Management:** Manage their program's billing and settings

### 4. REGULAR_USER
**Who:** Faculty, teaching assistants, program staff
**Scope:** Courses they have access to within their assigned program(s)
**Pricing:** Free
**Abilities:**
- **Data Entry:** Input course information via multiple methods
- **Course Management:** Create/edit courses they have access to
- **Basic Reporting:** Generate reports for their own courses
- **Profile Management:** Update their own account settings

## AI-Powered Data Entry Strategy

### Core Philosophy
**Minimize user effort, maximize accuracy** - Accept any input format and use AI to extract structured data.

### Expected Input Variability
- **Photos of documents** (handwritten notes, printed reports)
- **Excel spreadsheets** (various formats and layouts)
- **Email screenshots** (grade reports, enrollment summaries)
- **PDF reports** from LMS systems
- **Word documents** (syllabi, assessment reports)
- **Manual form entry** (traditional web forms as fallback)

### AI Processing Pipeline
1. **Input Classification:** Determine input type (image, document, structured data)
2. **Content Extraction:** OCR for images, parsing for documents
3. **Data Structure Recognition:** Identify key fields (course number, semester, grades, etc.)
4. **Validation & Confirmation:** Present extracted data to user for verification
5. **Learning Loop:** Improve extraction based on user corrections

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
