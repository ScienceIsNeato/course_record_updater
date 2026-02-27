# Data Model & Entity Relationships

## Core Entities & Relationships

### 1. **User**

**Purpose:** All people using the system, regardless of access level
**Key Attributes:**

- `user_id` (UUID, primary key)
- `email` (unique, used for login)
- `full_name`
- `role` (enum: 'site_admin', 'institution_admin', 'program_admin', 'instructor')
- `primary_institution_id` (foreign key → Institution, optional for site_admin, used for default context)
- `account_status` (enum: 'active', 'pending', 'suspended')
- `created_at`, `updated_at`
- `last_login_at`
- `registration_completed_at` (null for pending users)

**Authentication (null for pending users):**

- `password_hash` (for traditional auth, null for pending)
- `oauth_provider` (google, microsoft, etc., null for pending)
- `oauth_id` (external provider ID, null for pending)
- `email_verified_at` (null for pending)
- `two_factor_enabled` (false for pending)

**Payment Info (Future):**

- `stripe_customer_id` (for billing integration)
- `billing_email` (may differ from login email)

**Business Rules:**

- `account_status = 'pending'`: User record created by invitation, hasn't completed registration
- `account_status = 'active'`: User has completed registration and can log in
- `account_status = 'suspended'`: Account temporarily disabled
- Pending users cannot log in until they complete registration
- Users can have access to multiple institutions via UserProgramAccess records
- `primary_institution_id` determines default institution context in UI

### 2. **Institution**

**Purpose:** Top-level organizational unit (college, university)
**Key Attributes:**

- `institution_id` (UUID, primary key)
- `name` (e.g., "College of Eastern Idaho")
- `short_name` (e.g., "MockU")
- `website_url`
- `primary_accreditor` (e.g., "NWCCU")
- `created_at`, `updated_at`
- `is_active`

**Relationships:**

- Has many Programs
- Has many Users (via User.institution_id foreign key)

### 3. **Program**

**Purpose:** Department/academic program within an institution (new hierarchical layer)
**Key Attributes:**

- `program_id` (UUID, primary key)
- `name` (e.g., "Biology Department", "Computer Science Program")
- `short_name` (e.g., "BIO", "CS")
- `description` (optional program description)
- `institution_id` (foreign key → Institution)
- `created_by` (foreign key → User, program creator)
- `program_admins` (array of user_ids with admin access)
- `is_default` (boolean, true for "Unclassified" default program)
- `created_at`, `updated_at`
- `is_active`

**Relationships:**

- Belongs to one Institution
- Has many Courses (many-to-many relationship)
- Has many Program Admins (via program_admins array)
- Created by one User

**Business Rules:**

- Every institution has at least one program (default "Unclassified")
- Courses can belong to multiple programs
- Program admins can only manage courses within their assigned programs
- Institution admins can manage all programs within their institution

### 4. **Course** (Updated)

**Purpose:** Abstract course definition (e.g., "MATH-101 College Algebra")
**Key Attributes:**

- `course_id` (UUID, primary key)
- `course_number` (e.g., "MATH-101")
- `course_title` (e.g., "College Algebra")
- `department` (e.g., "MATH")
- `credit_hours` (default 3)
- `institution_id` (foreign key → Institution)
- `program_ids` (array of program_ids this course belongs to)
- `created_at`, `updated_at`

**Relationships:**

- Belongs to one Institution
- Belongs to multiple Programs (via program_ids array)
- Has many Course Offerings
- Has many Course Sections (through offerings)

**Business Rules:**

- Courses without explicit program assignment go to default "Unclassified" program
- Course can be shared across multiple programs within same institution
- Course number must be unique within institution

### 5. **CourseOffering** (Updated)

**Key Attributes:**

- `program_id` (UUID, primary key)
- `institution_id` (foreign key → Institution)
- `name` (e.g., "Biology Department", "Nursing Program")
- `code` (e.g., "BIOL", "NURS")
- `description`
- `governing_body` (enum: 'NWCCU')
- `created_at`, `updated_at`
- `is_active`

**Relationships:**

- Belongs to Institution
- Has many Courses
- Has many Users (via UserProgramAccess junction table)

### 4. **Course**

**Purpose:** Individual course record with all data needed for accreditation
**Key Attributes:**

- `course_id` (UUID, primary key)
- `program_id` (foreign key → Program)
- `institution_id` (foreign key → Institution, denormalized for performance)
- `created_by_user_id` (foreign key → User, course owner)
- `last_modified_by_user_id` (foreign key → User)
- `shared_with_user_ids` (array of user_ids who can view/edit this course)

**Course Identification (User-defined, flexible):**

- `course_number` (string, e.g., "BIOL-101", "FUCKFACE", whatever user wants)
- `course_title` (string, e.g., "Introduction to Biology")
- `semester` (string, e.g., "FALL", "SPRING", "SUM01", whatever user wants)
- `academic_year` (integer, e.g., 2024, 2025)
- `section` (string, optional, e.g., "01", "A", "LAB")

**Course Details:**

- `credit_hours` (decimal, optional)
- `course_modality` (string, e.g., "in_person", "online", "hybrid", or custom)
- `description` (text, optional, course description/notes)

**Enrollment & Assessment Data:**

- `total_students` (integer)
- `students_completed` (integer, optional)
- `students_withdrawn` (integer, optional)
- `grade_distribution` (JSON: {"A": 12, "B": 8, "C": 5, "D": 2, "F": 1})
- `custom_fields` (JSON: institution-defined additional fields)
- `assessment_methods` (text, optional)
- `improvement_actions` (text, optional)

**Unique Constraint:** `(program_id, course_number, semester, academic_year, section)`

**Metadata:**

- `created_at`, `updated_at`
- `is_archived` (for historical data)

### 5. **UserProgramAccess**

**Purpose:** Junction table for user access to programs (many-to-many)
**Key Attributes:**

- `user_program_access_id` (UUID, primary key)
- `user_id` (foreign key → User)
- `program_id` (foreign key → Program)
- `institution_id` (foreign key → Institution, denormalized for performance)
- `access_type` (enum: 'administrator', 'member')
- `granted_by_user_id` (foreign key → User, who granted this access)
- `granted_at` (timestamp)
- `revoked_at` (timestamp, null if active)
- `is_active` (boolean)

**Unique Constraint:** `(user_id, program_id)` - user can only have one access record per program

**Business Rules:**

- `access_type = 'administrator'`: User can manage the program (invite others, manage courses)
- `access_type = 'member'`: User can create/edit courses in the program
- Multi-program administrators get 'administrator' access only to programs they are explicitly assigned
- No automatic institution-wide access - each program assignment is explicit
- Site admins bypass this table entirely (global access)

### 6. **CourseOutcome (CLO)**

**Purpose:** Course Learning Outcomes - specific assessments within each course
**Key Attributes:**

- `course_outcome_id` (UUID, primary key)
- `course_id` (foreign key → Course)
- `program_id` (foreign key → Program, denormalized)
- `institution_id` (foreign key → Institution, denormalized)
- `created_by_user_id` (foreign key → User)
- `last_modified_by_user_id` (foreign key → User)

**CLO Identification:**

- `clo_number` (string, e.g., "1", "2", "3")
- `clo_code` (string, e.g., "ACC-201.1", "BIOL-101.2")
- `clo_description` (text, full outcome description)

**Assessment Data:**

- `assessment_tool` (text, how this CLO was measured)
- `students_took_assessment` (integer)
- `students_passed_assessment` (integer)
- `pass_rate_percentage` (calculated: passed ÷ took × 100)
- `pass_threshold` (integer, default 75)
- `result_status` (enum: 'S', 'U' based on threshold)

**Flexible Assessment Fields:**

- `assessment_tool` (text, how this CLO was measured)
- `narrative_data` (JSON, flexible structure for institution-specific fields)
  - Default: `{"celebrations": "", "challenges": "", "changes": ""}`
  - Customizable: institutions can define their own narrative categories
- `custom_fields` (JSON, institution-defined additional fields)

**Metadata:**

- `created_at`, `updated_at`
- `is_active` (boolean)

**Business Rules:**

- Multiple CLOs per course (1:many relationship)
- Each CLO assessed independently
- S/U determination based on pass_threshold (default 75%)
- CLO codes follow pattern: COURSE-###.# (e.g., ACC-201.1)

### 7. **CourseInstructor**

**Purpose:** Many-to-many relationship between courses and instructors
**Key Attributes:**

- `course_instructor_id` (UUID, primary key)
- `course_id` (foreign key → Course)
- `instructor_user_id` (foreign key → User, always required)
- `is_primary` (boolean, default false, one primary instructor per course)
- `added_by_user_id` (foreign key → User, who added this instructor)
- `added_at` (timestamp)
- `is_active` (boolean, default true)

**Business Rules:**

- `instructor_user_id` always references a User record (may be pending status)
- When instructor doesn't exist in system, create pending User record first
- Pending instructors cannot log in until they complete registration
- Active instructors can edit the course (if they accept course invitation)
- Multiple instructors allowed per course
- One instructor can be marked as `is_primary` for reporting purposes

### 8. **CourseInvitation**

**Purpose:** Secure invitation system for sharing individual courses
**Key Attributes:**

- `course_invitation_id` (UUID, primary key)
- `course_id` (foreign key → Course)
- `program_id` (foreign key → Program)
- `institution_id` (foreign key → Institution)
- `invited_by_user_id` (foreign key → User, course owner or admin)
- `invited_email` (email address being invited)
- `invitation_token` (UUID, secure token for the link)
- `expires_at` (timestamp, 7 days from creation)
- `accepted_at` (null if not yet accepted)
- `accepted_by_user_id` (foreign key → User, if accepted)
- `revoked_at` (null if still active)
- `created_at`

**Security Features:**

- Tokens expire after 7 days
- One-time use (marked as accepted when used)
- Can be revoked by the inviter or course owner
- Email verification required before acceptance

### 9. **ProgramInvitation**

**Purpose:** Secure invitation system for adding users to programs
**Key Attributes:**

- `invitation_id` (UUID, primary key)
- `program_id` (foreign key → Program)
- `institution_id` (foreign key → Institution)
- `invited_by_user_id` (foreign key → User)
- `invited_email` (email address being invited)
- `intended_role` (enum: role they'll get when they accept)
- `invitation_token` (UUID, secure token for the link)
- `expires_at` (timestamp, 7 days from creation)
- `accepted_at` (null if not yet accepted)
- `accepted_by_user_id` (foreign key → User, if accepted)
- `revoked_at` (null if still active)
- `created_at`

**Security Features:**

- Tokens expire after 7 days
- One-time use (marked as accepted when used)
- Can be revoked by the inviter
- Email verification required before acceptance

### 10. **FormConfiguration**

**Purpose:** Institution and program-level form customization
**Key Attributes:**

- `form_config_id` (UUID, primary key)
- `institution_id` (foreign key → Institution)
- `program_id` (foreign key → Program, optional - null for institution-wide)
- `form_type` (enum: 'course', 'clo', 'assessment')
- `created_by_user_id` (foreign key → User)
- `last_modified_by_user_id` (foreign key → User)

**Form Structure:**

- `field_definitions` (JSON array of field configurations)
- `field_order` (array, defines field display order)
- `validation_rules` (JSON, custom validation logic)
- `conditional_logic` (JSON, show/hide field dependencies)

**Metadata:**

- `created_at`, `updated_at`
- `is_active` (boolean)
- `version` (integer, for form versioning)

**Business Rules:**

- Program-level configs override institution-level configs
- Form versioning maintains historical data integrity
- Institution admins can create/modify form configs
- Program admins can only modify program-specific configs

### 11. **CustomField**

**Purpose:** Dynamic field definitions for flexible data collection
**Key Attributes:**

- `custom_field_id` (UUID, primary key)
- `institution_id` (foreign key → Institution)
- `program_id` (foreign key → Program, optional)
- `entity_type` (enum: 'course', 'clo', 'assessment')
- `field_name` (string, unique within scope)
- `field_type` (enum: 'text', 'number', 'dropdown', 'multi_select', 'date', 'boolean')
- `field_label` (string, display name)
- `is_required` (boolean)
- `default_value` (text, optional)
- `validation_rules` (JSON, field-specific validation)
- `dropdown_options` (JSON array, for dropdown/multi_select types)
- `help_text` (text, optional)
- `display_order` (integer)
- `created_by_user_id` (foreign key → User)

**Metadata:**

- `created_at`, `updated_at`
- `is_active` (boolean)

**Business Rules:**

- Custom fields are institution or program scoped
- Field names must be unique within scope and entity type
- Dropdown options stored as JSON array
- Validation rules stored as JSON for flexibility

### 12. **Report** (Future)

**Purpose:** Generated accreditation reports and templates
**Key Attributes:**

- `report_id` (UUID, primary key)
- `program_id` (foreign key → Program)
- `institution_id` (foreign key → Institution)
- `generated_by_user_id` (foreign key → User)
- `report_type` (e.g., "NWCCU_Annual", "HLC_Assessment")
- `academic_year`
- `course_ids_included` (JSON array of course IDs)
- `generated_at`
- `report_data` (JSON: the actual report content)
- `export_format` (enum: 'pdf', 'word', 'excel')
- `file_url` (link to generated file)

## Key Relationships

### User Access Pattern

```
User → UserProgramAccess → Program → Courses
User → Course (via created_by_user_id or shared_with_user_ids)
```

### Data Hierarchy

```
Institution (1) → (many) Programs (1) → (many) Courses (1) → (many) CourseOutcomes (CLOs)
                                                        (1) → (many) CourseInstructors
                (1) → (many) FormConfigurations
                (1) → (many) CustomFields
```

### Invitation Flows

```
# Program Access
ProgramAdmin → ProgramInvitation → Email → NewUser/ExistingUser → UserProgramAccess

# Course Sharing
CourseOwner → CourseInvitation → Email → NewUser/ExistingUser → Course.shared_with_user_ids

# Instructor Assignment
CourseOwner → Add Instructor → Create Pending User → CourseInstructor created → Email Invitation → User completes registration → User.account_status = 'active'
```

## User Experience & Access Control

### Program Selection Logic

**For Course Creation:**

- **Institution Administrator:** Shows dropdown of all programs in their institution(s)
- **Program Administrator:**
  - If assigned to only 1 program: Program auto-selected (hidden field)
  - If assigned to multiple programs: Shows dropdown of their assigned programs
- **Regular User:**
  - If member of only 1 program: Program auto-selected (hidden field)
  - If member of multiple programs: Shows dropdown of their accessible programs

**Business Rule:** A course belongs to exactly one program

### Row-Level Security

- All queries automatically filter by user's accessible programs
- Institution admins see all programs in their institution
- Program admins see only their assigned programs
- Regular users see only programs they're members of

### Invitation Security

- Invitation tokens are UUIDs (non-guessable)
- 7-day expiration
- One-time use
- Email verification required
- Can handle both new user signup and existing user addition

### Audit Trail

- All course modifications tracked via `last_modified_by_user_id`
- Invitation grants tracked via `granted_by_user_id`
- Timestamps on all major actions

## Questions to Resolve

1. **Multi-Instructor Courses:** How do we handle team-taught courses?
   - Just use `instructor_name` field (may differ from `created_by_user_id`)?
   - Allow multiple people to edit the same course instance?

2. **Data Retention:** How long do we keep:
   - Revoked user access records?
   - Expired invitations?
   - Archived course instances?

3. **Accreditor Flexibility:** Should `learning_outcomes_data` be:
   - Completely flexible JSON?
   - Semi-structured with common fields + custom fields?
   - Separate tables per accreditor?
