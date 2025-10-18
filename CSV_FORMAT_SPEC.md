# Generic CSV Adapter - Format Specification v1.0

## Overview

The generic CSV adapter exports/imports data as a ZIP file containing multiple normalized CSV files, one per entity type. This follows standard database export patterns (similar to PostgreSQL dumps).

## File Structure

```
generic_export_YYYYMMDD_HHMMSS.zip
├── manifest.json
├── institutions.csv
├── users.csv
├── programs.csv
├── user_programs.csv
├── courses.csv
├── course_programs.csv
├── terms.csv
├── course_offerings.csv
├── course_sections.csv
├── course_outcomes.csv
└── user_invitations.csv
```

## Import Order (Respects Foreign Keys)

1. **institutions.csv** (no dependencies)
2. **programs.csv** (depends on: institutions)
3. **users.csv** (depends on: institutions)
4. **user_programs.csv** (depends on: users, programs)
5. **courses.csv** (depends on: institutions)
6. **course_programs.csv** (depends on: courses, programs)
7. **terms.csv** (depends on: institutions)
8. **course_offerings.csv** (depends on: courses, terms, institutions)
9. **course_sections.csv** (depends on: course_offerings, users)
10. **course_outcomes.csv** (depends on: courses)
11. **user_invitations.csv** (depends on: institutions)

---

## CSV File Schemas

### 1. manifest.json

Metadata about the export.

```json
{
  "format_version": "1.0",
  "export_timestamp": "2024-10-05T22:00:00Z",
  "institution_id": "mocku-uuid",
  "institution_name": "Example University",
  "adapter_id": "generic_csv_v1",
  "entity_counts": {
    "institutions": 1,
    "programs": 5,
    "users": 125,
    "courses": 150,
    "terms": 2,
    "course_offerings": 300,
    "course_sections": 450,
    "course_outcomes": 600,
    "user_invitations": 10
  },
  "import_order": [
    "institutions.csv",
    "programs.csv",
    "users.csv",
    "user_programs.csv",
    "courses.csv",
    "course_programs.csv",
    "terms.csv",
    "course_offerings.csv",
    "course_sections.csv",
    "course_outcomes.csv",
    "user_invitations.csv"
  ]
}
```

### 2. institutions.csv

**Table**: `institutions`

**Columns**:
```csv
id,name,short_name,website_url,created_by,admin_email,allow_self_registration,require_email_verification,is_active,created_at,updated_at
```

**Foreign Keys**: None

**Example**:
```csv
id,name,short_name,website_url,created_by,admin_email,allow_self_registration,require_email_verification,is_active,created_at,updated_at
mocku-123,Example University,MockU,https://example.edu,admin-001,admin@example.edu,false,true,true,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
```

### 3. programs.csv

**Table**: `programs`

**Columns**:
```csv
id,name,short_name,description,institution_id,created_by,is_default,is_active,created_at,updated_at
```

**Foreign Keys**:
- `institution_id` → `institutions.id`

**Example**:
```csv
id,name,short_name,description,institution_id,created_by,is_default,is_active,created_at,updated_at
prog-1,Computer Science Program,CS,Undergraduate CS Program,mocku-123,admin-001,true,true,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
prog-2,Nursing Program,RN,Registered Nurse Program,mocku-123,admin-001,false,true,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
```

### 4. users.csv

**Table**: `users`

**Columns**:
```csv
id,email,first_name,last_name,display_name,role,institution_id,invited_by,invited_at,registration_completed_at,oauth_provider,created_at,updated_at
```

**Excluded Sensitive Fields** (always omitted for security):
- `password_hash` - Excluded (security risk)
- `password_reset_token` - Excluded (active security token)
- `password_reset_expires_at` - Excluded (related to token)
- `email_verification_token` - Excluded (active security token)

**Import Behavior**:
- Imported users are created with `account_status: "pending"`
- Imported users have `email_verified: false`
- Users must complete invitation/registration flow to set password
- `login_attempts`, `locked_until`, `last_login_at` reset to defaults

**Foreign Keys**:
- `institution_id` → `institutions.id`
- `invited_by` → `users.id` (self-reference)

**Example**:
```csv
id,email,first_name,last_name,display_name,role,institution_id,invited_by,invited_at,registration_completed_at,oauth_provider,created_at,updated_at
user-1,john.doe@example.edu,John,Doe,,instructor,mocku-123,,,2024-08-01T00:00:00Z,,2024-08-01T00:00:00Z,2024-10-01T00:00:00Z
```

**Security Note**: This adapter prioritizes security over immediate usability. Imported users must complete the invitation/registration workflow.

### 5. user_programs.csv

**Table**: `user_programs` (many-to-many association)

**Columns**:
```csv
user_id,program_id
```

**Foreign Keys**:
- `user_id` → `users.id`
- `program_id` → `programs.id`

**Example**:
```csv
user_id,program_id
user-1,prog-1
user-2,prog-1
user-2,prog-2
```

### 6. courses.csv

**Table**: `courses`

**Columns**:
```csv
id,course_number,course_title,department,credit_hours,institution_id,active,created_at,updated_at
```

**Foreign Keys**:
- `institution_id` → `institutions.id`

**Example**:
```csv
id,course_number,course_title,department,credit_hours,institution_id,active,created_at,updated_at
course-1,CS101,Introduction to Programming,Computer Science,3,mocku-123,true,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
course-2,NUR201,Fundamentals of Nursing,Nursing,4,mocku-123,true,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
```

### 7. course_programs.csv

**Table**: `course_programs` (many-to-many association)

**Columns**:
```csv
course_id,program_id
```

**Foreign Keys**:
- `course_id` → `courses.id`
- `program_id` → `programs.id`

**Example**:
```csv
course_id,program_id
course-1,prog-1
course-2,prog-2
```

### 8. terms.csv

**Table**: `terms`

**Columns**:
```csv
id,term_name,name,start_date,end_date,assessment_due_date,active,institution_id,created_at,updated_at
```

**Foreign Keys**:
- `institution_id` → `institutions.id`

**Note**: Both `term_name` and `name` columns exist in schema (legacy compatibility).

**Example**:
```csv
id,term_name,name,start_date,end_date,assessment_due_date,active,institution_id,created_at,updated_at
term-1,FA2024,Fall 2024,2024-08-26,2024-12-15,2024-12-20,true,mocku-123,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
term-2,SP2025,Spring 2025,2025-01-13,2025-05-10,2025-05-15,true,mocku-123,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
```

### 9. course_offerings.csv

**Table**: `course_offerings`

**Columns**:
```csv
id,course_id,term_id,institution_id,status,capacity,total_enrollment,section_count,created_at,updated_at
```

**Foreign Keys**:
- `course_id` → `courses.id`
- `term_id` → `terms.id`
- `institution_id` → `institutions.id`

**Example**:
```csv
id,course_id,term_id,institution_id,status,capacity,total_enrollment,section_count,created_at,updated_at
off-1,course-1,term-1,mocku-123,active,75,50,2,2024-08-01T00:00:00Z,2024-09-01T00:00:00Z
off-2,course-2,term-1,mocku-123,active,60,45,2,2024-08-01T00:00:00Z,2024-09-01T00:00:00Z
```

### 10. course_sections.csv

**Table**: `course_sections`

**Columns**:
```csv
id,offering_id,instructor_id,section_number,enrollment,status,grade_distribution,assigned_date,completed_date,created_at,updated_at
```

**Foreign Keys**:
- `offering_id` → `course_offerings.id`
- `instructor_id` → `users.id`

**Note**: `grade_distribution` is JSON - serialize as JSON string in CSV.

**Example**:
```csv
id,offering_id,instructor_id,section_number,enrollment,status,grade_distribution,assigned_date,completed_date,created_at,updated_at
section-1,off-1,user-1,001,25,in_progress,{},2024-08-01T00:00:00Z,,2024-08-01T00:00:00Z,2024-09-15T00:00:00Z
section-2,off-1,user-2,002,25,in_progress,{},2024-08-01T00:00:00Z,,2024-08-01T00:00:00Z,2024-09-15T00:00:00Z
```

### 11. course_outcomes.csv

**Table**: `course_outcomes`

**Columns**:
```csv
id,course_id,clo_number,description,assessment_method,active,assessment_data,narrative,created_at,updated_at
```

**Foreign Keys**:
- `course_id` → `courses.id`

**Note**: `assessment_data` is JSON - serialize as JSON string in CSV.

**Example**:
```csv
id,course_id,clo_number,description,assessment_method,active,assessment_data,narrative,created_at,updated_at
outcome-1,course-1,CLO1,Students will understand basic programming concepts,Written Exam,true,{},,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
outcome-2,course-1,CLO2,Students will write simple programs,Programming Assignment,true,{},,2024-01-01T00:00:00Z,2024-10-01T00:00:00Z
```

### 12. user_invitations.csv

**Table**: `user_invitations`

**Columns**:
```csv
id,email,role,institution_id,invited_by,invited_at,status,accepted_at,personal_message,created_at,updated_at
```

**Excluded Sensitive Fields**:
- `token` - Excluded (active security token)
- `expires_at` - Excluded (will be regenerated on import)

**Import Behavior**:
- New invitation tokens are generated on import
- Expiration dates are set to 14 days from import time
- Only `pending` invitations are imported (accepted/expired invitations are skipped)

**Foreign Keys**:
- `institution_id` → `institutions.id`
- `invited_by` → `users.id`

**Example**:
```csv
id,email,role,institution_id,invited_by,invited_at,status,accepted_at,personal_message,created_at,updated_at
inv-1,new.instructor@example.edu,instructor,mocku-123,user-1,2024-10-01T00:00:00Z,pending,,Welcome to our institution!,2024-10-01T00:00:00Z,2024-10-01T00:00:00Z
```

**Security Note**: Invitation tokens are regenerated on import to prevent token reuse attacks.

---

## CSV Formatting Standards

### NULL Values
- Empty string: `""`
- Omitted optional fields: `,,` (consecutive commas)

### Booleans
- `true` / `false` (lowercase)

### Dates/Timestamps
- ISO 8601 format: `2024-10-05T22:00:00Z`
- Always UTC timezone

### JSON Fields
- Serialize as JSON string: `"{\"key\":\"value\"}"`
- Quote the entire JSON string in CSV
- Empty JSON object: `{}`

### Strings with Commas/Quotes
- Follow CSV RFC 4180 standard
- Quote fields containing commas: `"Last, First"`
- Escape quotes by doubling: `"He said ""hello"""`

---

## Security & Privacy

### Sensitive Data Exclusion

**Always Excluded Fields** (security-first approach):
- User passwords: `password_hash`
- Active tokens: `password_reset_token`, `email_verification_token`, `invitation.token`
- Token expiration: `password_reset_expires_at`, `invitation.expires_at`

**Rationale**: This adapter prioritizes security over immediate usability. Users must complete registration/invitation workflows after import.

**Trade-off**: Imported users cannot immediately login. They must:
1. Complete email verification OR
2. Accept new invitation OR  
3. Complete password reset flow

This is the **most secure** approach and prevents:
- Password hash exposure in transit
- Token reuse attacks
- Stale authentication state

### Extras Column Handling

The `extras` column (PickleType) is serialized as JSON:
- Export: Convert PickleType → JSON string
- Import: Parse JSON string → dict → save as extras
- Empty extras: `{}`

## Implementation Notes

### Export Process
1. Query database for each entity type
2. **Exclude sensitive fields** (passwords, tokens)
3. **Serialize extras as JSON**
4. Convert to CSV (one file per entity)
5. Create manifest.json with counts
6. ZIP all files together
7. Return ZIP file

### Import Process
1. Extract ZIP to temporary directory
2. Read manifest.json (validate version)
3. Parse each CSV in dependency order
4. **Generate new tokens** for invitations
5. **Set imported users to "pending" status**
6. **Deserialize JSON extras**
7. Create records in database
8. Handle foreign key references
9. Clean up temporary files

### Error Handling
- **Invalid foreign keys**: Skip record, log error
- **Duplicate IDs**: Skip record, log warning (or update if conflict resolution enabled)
- **Missing required fields**: Skip record, log error
- **Malformed CSV**: Abort import, report line number

---

## Version History

**v1.0** (2024-10-05)
- Initial specification
- 12 CSV files covering all core entities
- ZIP-based single-file export/import
- JSON manifest for metadata
- Security-first: Excludes passwords and active tokens
- Extras columns serialized as JSON

