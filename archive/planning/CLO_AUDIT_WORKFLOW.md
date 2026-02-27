# CLO Submission and Audit Workflow Implementation

## Overview

Add a complete submission-to-approval pipeline for Course Learning Outcomes (CLOs), enabling instructors to submit their work for review and admins/institution admins to audit and approve submissions with feedback capability.

## CLO Status Lifecycle

Implement 6-state lifecycle:

1. **UNASSIGNED**: CLOs exist but course section has no instructor
2. **ASSIGNED**: CLOs exist, instructor assigned (ready to work)
3. **IN_PROGRESS**: Instructor has started editing (auto-set on first edit)
4. **AWAITING_APPROVAL**: Instructor submitted for review
5. **APPROVAL_PENDING**: Sent back for rework with feedback
6. **APPROVED**: Final approval granted

## Database Changes

### models_sql.py

Add to `CourseOutcome` model:

- `status` field (enum: assigned, in_progress, awaiting_approval, approval_pending, approved)
- `submitted_at` (timestamp)
- `submitted_by_user_id` (foreign key)
- `reviewed_at` (timestamp)
- `reviewed_by_user_id` (foreign key)
- `approval_status` (enum: pending, approved, needs_rework)
- `feedback_comments` (text, for rework requests)
- `feedback_provided_at` (timestamp)

### Migration Script

Create alembic migration to add new columns to existing `course_outcomes` table with safe defaults.

## Backend Services

### New Service: `clo_workflow_service.py`

```python
# Core workflow operations:
- submit_clo_for_approval(outcome_id, user_id) -> bool
- approve_clo(outcome_id, reviewer_id) -> bool
- request_rework(outcome_id, reviewer_id, comments, send_email=False) -> bool
- get_clos_awaiting_approval(institution_id, program_id=None) -> List[Dict]
- get_clos_by_status(status, filters) -> List[Dict]
- auto_mark_in_progress(outcome_id, user_id) -> bool
```

### Email Integration

Extend `email_service.py` or `bulk_email_service.py`:

- `send_rework_notification(instructor_email, clo_details, feedback_comments)`
- Use existing email infrastructure
- Include CLO details, feedback, and link to edit form

### Database Service Extensions (`database_service.py`)

Add methods:

- `update_clo_status(outcome_id, status, user_id, **kwargs)`
- `get_outcomes_by_status(institution_id, status, program_id=None)`
- `get_outcome_with_course_details(outcome_id)` (for rich audit view)

## API Routes (`api_routes.py`)

Add new endpoints:

```python
# Instructor actions
POST /api/outcomes/<outcome_id>/submit
  - Submit CLO for approval
  - Requires: instructor role, owns the course section

# Admin audit actions
GET /api/outcomes/audit
  - List CLOs awaiting approval (filtered by institution/program)
  - Returns: enriched data (course info, instructor info, submission date)

POST /api/outcomes/<outcome_id>/approve
  - Approve a CLO
  - Requires: admin or institution_admin role

POST /api/outcomes/<outcome_id>/request-rework
  - Request rework with feedback
  - Body: {comments: str, send_email: bool}
  - Requires: admin or institution_admin role

GET /api/outcomes/<outcome_id>/audit-details
  - Get full audit details for single CLO
  - Includes: course, instructor, submission history, feedback history
```

## Frontend - Instructor Experience

### Modify `templates/assessments.html`

1. **Auto-tracking**: When instructor edits any assessment field, auto-set status to `IN_PROGRESS`
2. **Submit Button**: Add "Submit for Approval" button for each CLO
3. **Status Indicators**: Show current status badge (In Progress, Awaiting Approval, Needs Rework, Approved)
4. **Feedback Display**: If status is APPROVAL_PENDING, show feedback comments prominently
5. **Resubmit Flow**: After addressing feedback, allow resubmission

### Update `static/` JavaScript

Create or modify assessment form handling:

- Track field edits to set IN_PROGRESS status
- Handle submission confirmation dialog
- Show feedback in a clear, actionable way

## Frontend - Admin Audit Interface

### New Dashboard Panel

Add to `templates/dashboard/program_admin.html` and `templates/dashboard/institution_admin.html`:

**Panel: "CLO Audit & Approval"**

- Only visible to program_admin and institution_admin roles
- Summary stats: X pending, Y approved this term, Z needing rework
- Quick action button: "Review Submissions"

### New Template: `templates/audit_clo.html`

Dedicated full-page audit interface:

**Summary View:**

- Table of CLOs awaiting approval
- Columns: Course, Instructor, CLO#, Description (truncated), Submitted Date
- Status filter: All / Awaiting Approval / Needs Rework
- Sortable by date, course, instructor
- Click row to expand or navigate to detail view

**Detail View (modal or inline expand):**

- Full CLO information
- Assessment data (students assessed, meeting target, narrative)
- Instructor who submitted
- Submission timestamp
- Previous feedback (if resubmission)
- Action buttons:
  - **Approve**: Green button, confirms and approves
  - **Request Rework**: Yellow button, opens feedback form

**Rework Feedback Form:**

- Multi-line text area for comments (required)
- Checkbox: "Send email notification to instructor"
- Submit button: "Send for Rework"

### Bulk Actions (Future Enhancement)

Document in plan but defer implementation:

- Checkbox selection for multiple CLOs
- "Approve Selected" bulk action
- Keep individual review as primary workflow initially

## Permissions & Access Control

### auth_service.py Updates

Ensure permission checks:

- `SUBMIT_CLO`: Instructors can submit CLOs for their own course sections
- `AUDIT_CLO`: Program admins can audit CLOs in their programs
- `AUDIT_ALL_CLO`: Institution admins can audit all CLOs at institution

Add to existing permission structure (if not already present).

## UAT Test Cases

Create 4 new E2E test files in `tests/e2e/`:

### `test_uat_007_clo_submission_happy_path.py`

1. Seed: Institution, program, course, section with instructor, CLOs in ASSIGNED status
2. Instructor logs in
3. Navigate to assessments page
4. Edit CLO fields (verify auto-set to IN_PROGRESS)
5. Submit CLO for approval
6. Verify status = AWAITING_APPROVAL, submitted_at set

### `test_uat_008_clo_approval_workflow.py`

1. Seed: CLOs in AWAITING_APPROVAL status
2. Admin logs in
3. Navigate to audit dashboard panel
4. Open audit interface
5. Select CLO from list
6. Click "Approve"
7. Verify status = APPROVED, reviewed_at set

### `test_uat_009_clo_rework_feedback.py`

1. Seed: CLOs in AWAITING_APPROVAL status
2. Admin logs in, navigates to audit interface
3. Select CLO, click "Request Rework"
4. Enter feedback comments
5. Check "Send email notification"
6. Submit
7. Verify:
   - Status = APPROVAL_PENDING
   - Feedback stored
   - Email sent (check via API or email provider)
8. Instructor logs in, sees feedback
9. Makes edits, resubmits
10. Verify status back to AWAITING_APPROVAL

### `test_uat_010_clo_pipeline_end_to_end.py`

Full lifecycle test:

1. Create course section with CLOs (UNASSIGNED)
2. Assign instructor (→ ASSIGNED)
3. Instructor edits (→ IN_PROGRESS)
4. Instructor submits (→ AWAITING_APPROVAL)
5. Admin requests rework (→ APPROVAL_PENDING)
6. Instructor addresses and resubmits (→ AWAITING_APPROVAL)
7. Admin approves (→ APPROVED)
8. Verify audit trail in database

## Implementation Order

1. **Database schema** (migration + model updates)
2. **Backend service** (clo_workflow_service.py)
3. **API routes** (CRUD + workflow endpoints)
4. **Unit tests** for service and routes
5. **Instructor UI** (assessments.html updates)
6. **Admin audit panel** (dashboard additions)
7. **Admin audit page** (dedicated audit_clo.html)
8. **Email integration** (rework notifications)
9. **E2E UAT tests** (4 test files)
10. **Documentation updates** (STATUS.md, user guides)

## Key Files to Create/Modify

**New Files:**

- `clo_workflow_service.py`
- `templates/audit_clo.html`
- `static/audit_clo.js`
- `tests/e2e/test_uat_007_clo_submission_happy_path.py`
- `tests/e2e/test_uat_008_clo_approval_workflow.py`
- `tests/e2e/test_uat_009_clo_rework_feedback.py`
- `tests/e2e/test_uat_010_clo_pipeline_end_to_end.py`
- `tests/unit/test_clo_workflow_service.py`
- Database migration file (alembic)

**Modified Files:**

- `models_sql.py` (add fields to CourseOutcome)
- `models.py` (update Firestore schema if still used)
- `database_service.py` (add CLO status query methods)
- `api_routes.py` (add workflow endpoints)
- `templates/assessments.html` (instructor submission UI)
- `templates/dashboard/program_admin.html` (audit panel)
- `templates/dashboard/institution_admin.html` (audit panel)
- `auth_service.py` (permission checks)
- `email_service.py` or `bulk_email_service.py` (rework notifications)
- `constants.py` (CLO status enums)

## Success Criteria

- Instructors can submit CLOs and see status changes
- Admins can view pending CLOs in dedicated audit interface
- Admins can approve or request rework with comments
- Email notifications sent when rework requested (if checkbox selected)
- Full lifecycle works: assigned → in_progress → submitted → rework → resubmit → approved
- All 4 UAT tests pass
- No instructor access to audit views
- Audit trail captured in database (submitted_by, reviewed_by, timestamps)
