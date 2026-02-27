# CEI Demo Follow-ups - Implementation Plan

**Created:** November 2025  
**Target Completion:** End of Winter 2026 (for UAT handoff)  
**Go-Live:** Mid-April 2026

---

## 🔥 Greenfield Project Note

**This is a greenfield, unreleased project.** We have ZERO backward compatibility concerns until CEI onboards in April 2026.

**Approach:**

- ✅ Update schemas directly in model files
- ✅ Nuke and rebuild databases at will
- ✅ Update seed scripts to match new schema
- ❌ NO migration scripts needed
- ❌ NO data preservation concerns
- ❌ NO gradual rollout complexity

**Freedom:** We can make breaking changes cleanly without worrying about existing production data.

---

## Overview

This plan implements the 7 actionable items identified from the October 2025 CEI demo feedback. The work is organized into 4 phases with clear dependencies and deliverables.

**Total Items:** 2 CRITICAL, 4 HIGH, 1 LOW

---

## Phase 1: Database Schema Redesign (CRITICAL - Week 1-2)

This phase addresses fundamental data model errors and must be completed before any other work.

**🔥 GREENFIELD APPROACH:** No migration scripts needed. We'll update the schema directly and nuke/reseed databases.

### 1.1 CLO Assessment Data Model Changes

**Issue:** Currently tracks `students_passing` against `enrollment`. Leslie needs `students_took` vs. `students_passed`.

**Database Changes:**

```python
# Current (WRONG):
class CourseOutcome:
    enrollment: int  # Pre-populated from feed
    students_passing: int  # Instructor enters
    # Missing: students_took

# Required (CORRECT):
class CourseOutcome:
    # CLO Assessment Fields
    students_took: int  # NEW - How many took this CLO assessment
    students_passed: int  # RENAME from students_passing
    assessment_tool: str  # NEW - 40-50 char limit (e.g., "Test #3", "Lab 2")
    # REMOVE: narrative field (was never supposed to be here)
```

**Validation Logic:**

- `students_took <= course.enrollment`
- `students_passed <= students_took`
- `students_passed >= 0`
- `students_took >= 0`

**Affected Files:**

- `models.py` or `models_sql.py` (CourseOutcome model - direct schema change)
- `database_sqlite.py` (queries)
- `database_service.py` (data access layer)
- `scripts/seed_db.py` (update seed script for new schema)

**Implementation Strategy:**

1. Update model definitions directly
2. Delete existing `.db` files
3. Update seed script to populate new fields
4. Recreate databases with `./restart_server.sh dev` or seed script
5. Update test fixtures to use new schema

**No Backward Compatibility:** Clean slate - just change the schema and rebuild databases.

**Testing Requirements:**

- Unit tests for validation logic
- Integration tests for data access
- Test seed script with new schema

---

### 1.2 Course-Level Enrollment and Narrative Section

**Issue:** No course-level summary section. Narratives incorrectly placed at CLO level.

**Database Changes:**

```python
# New Model or extend existing Course/Section model
class CourseAssessmentSummary:
    course_id: str  # FK to Course

    # Enrollment Data (pre-populated from feed)
    enrollment: int  # Read-only for instructor
    withdrawals: int  # Read-only for instructor

    # Instructor-Entered Grade Data
    students_passed: int  # Students with A, B, C
    students_dfic: int  # Students with D, F, Incomplete
    cannot_reconcile: bool  # DEFAULT False
    reconciliation_note: str  # Optional, when cannot_reconcile=True

    # Course-Level Narratives (was incorrectly at CLO level)
    narrative_celebrations: str  # Free text
    narrative_challenges: str  # Free text
    narrative_changes: str  # Free text - planned for next offering

    # Calculated
    pass_rate: float  # (students_passed / (enrollment - withdrawals)) * 100
```

**Validation Logic:**

- `students_passed + students_dfic == enrollment - withdrawals` (unless `cannot_reconcile=True`)
- If `cannot_reconcile=True`, require `reconciliation_note` (min 10 chars)
- All narrative fields: free text, no length limit (but reasonable UI limits)

**Affected Files:**

- `models.py` or `models_sql.py` (new CourseAssessmentSummary model or extend Course)
- `database_sqlite.py` (CRUD operations)
- `database_service.py` (data access layer)
- `scripts/seed_db.py` (update seed script for new schema)

**Implementation Strategy:**

1. Create new model or extend existing Course model
2. Update seed script to populate default values
3. Nuke databases and recreate with new schema
4. **CLO narratives:** Just delete them - they were never supposed to be there

**Testing Requirements:**

- Unit tests for validation logic (especially cannot_reconcile bypass)
- Integration tests for course summary CRUD
- Test enrollment reconciliation scenarios

---

## Phase 2: UI and Workflow Updates (CRITICAL - Week 3-4)

This phase updates the instructor data entry workflow to match the new data model.

### 2.1 Instructor Assessment Entry UI Redesign

**Current State:** `templates/assessments.html` with incorrect CLO-level narrative

**Required Changes:**

**A. Course-Level Section (NEW - add at top):**

```html
<!-- Course Summary Section -->
<div class="course-summary-section">
  <h3>Course Enrollment Summary</h3>

  <!-- Read-only enrollment info -->
  <div class="enrollment-info">
    <span>Total Enrollment: {{ course.enrollment }}</span>
    <span>Withdrawals: {{ course.withdrawals }}</span>
  </div>

  <!-- Instructor-entered grade data -->
  <label>Number of Students Who Passed (A, B, C):</label>
  <input type="number" name="students_passed" min="0" required />

  <label>Number of Students with D/F/Incomplete:</label>
  <input type="number" name="students_dfic" min="0" required />

  <!-- Reconciliation checkbox -->
  <div class="reconciliation-section">
    <label>
      <input type="checkbox" name="cannot_reconcile" id="cannotReconcile" />
      Numbers don't reconcile (check if enrollment math doesn't add up)
    </label>
    <textarea
      name="reconciliation_note"
      id="reconciliationNote"
      placeholder="Brief explanation (e.g., 'Late drop not in system')"
      style="display:none;"
    ></textarea>
  </div>

  <!-- Course-level narratives -->
  <h4>Course Reflection</h4>

  <label>Celebrations (What went well?):</label>
  <textarea name="narrative_celebrations" rows="4"></textarea>

  <label>Challenges (What was difficult?):</label>
  <textarea name="narrative_challenges" rows="4"></textarea>

  <label>Changes (What will you do differently next time?):</label>
  <textarea name="narrative_changes" rows="4"></textarea>
</div>
```

**B. CLO Assessment Section (MODIFIED - update per CLO):**

```html
<!-- For each CLO -->
<div class="clo-assessment">
  <h4>CLO {{ clo.number }}: {{ clo.description }}</h4>

  <!-- CHANGED: assessment tool instead of narrative -->
  <label>Assessment Tool (40-50 characters):</label>
  <input
    type="text"
    name="assessment_tool_{{ clo.id }}"
    maxlength="50"
    placeholder="e.g., Test #3, Final Project, Lab 2"
    required
  />

  <!-- NEW: students_took field -->
  <label>Number of Students Who Took This Assessment:</label>
  <input
    type="number"
    name="students_took_{{ clo.id }}"
    min="0"
    max="{{ course.enrollment }}"
    required
  />

  <!-- RENAMED: students_passing → students_passed -->
  <label>Number of Students Who Passed This Assessment:</label>
  <input type="number" name="students_passed_{{ clo.id }}" min="0" required />

  <!-- Auto-calculated percentage (display only) -->
  <div class="calculated-percentage">
    Pass Rate: <span id="pass_rate_{{ clo.id }}">--%</span>
  </div>

  <!-- REMOVED: narrative field (was never supposed to be here) -->
</div>
```

**JavaScript Changes:**

- Add client-side validation: `students_took <= enrollment`
- Add client-side validation: `students_passed <= students_took`
- Auto-calculate and display pass percentage as user types
- Show/hide `reconciliation_note` textarea when checkbox changes
- Validate enrollment reconciliation: `passed + DFIC == enrollment - withdrawals` (unless cannot_reconcile=True)

**Affected Files:**

- `templates/assessments.html` (major restructuring)
- `static/assessments.js` (new validation logic)
- `api_routes.py` or `api/routes/*.py` (update POST handler)
- `tests/javascript/unit/assessments.test.js` (update tests)
- `tests/e2e/test_uat_*.py` (update E2E tests)

**Testing Requirements:**

- Unit tests for JavaScript validation
- E2E tests for full instructor workflow
- Test cannot_reconcile bypass logic
- Test all validation edge cases

---

## Phase 3: Audit Workflow Enhancements (HIGH - Week 5-6)

### 3.1 Add "Never Coming In" (NCI) Status

**Issue:** Leslie needs to close out submissions from instructors who disappeared without them showing as "pending" forever.

**Database Changes:**

```python
# Update audit status enum
class AuditStatus(Enum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    NEEDS_REWORK = "needs_rework"
    APPROVED = "approved"
    NEVER_COMING_IN = "never_coming_in"  # NEW
```

**UI Changes:**

**A. Audit Interface (`templates/audit_clo.html`):**

```html
<!-- Add third button to modal -->
<button class="btn-nci" onclick="markAsNCI('{{ outcome.id }}')">
  Mark as Never Coming In
</button>

<!-- NCI confirmation modal -->
<div id="nciModal">
  <h3>Mark as Never Coming In?</h3>
  <p>This submission will be closed out and removed from pending counts.</p>
  <label>Reason (optional):</label>
  <select name="nci_reason">
    <option value="instructor_left">Instructor Left Institution</option>
    <option value="non_responsive">Instructor Non-Responsive</option>
    <option value="course_cancelled">Course Cancelled</option>
    <option value="other">Other</option>
  </select>
  <textarea name="nci_note" placeholder="Additional notes..."></textarea>
  <button onclick="confirmNCI()">Confirm</button>
  <button onclick="cancelNCI()">Cancel</button>
</div>
```

**B. Dashboard Updates:**

- Add "Never Coming In" count to summary stats
- Filter options: Show/hide NCI items
- Visual indicator: Gray out NCI items in list
- Completion tracking: Exclude NCI from "pending" count but track separately

**Affected Files:**

- `models.py` (AuditStatus enum)
- `clo_workflow_service.py` (add `mark_as_nci()` method)
- `api/routes/clo_workflow.py` (new endpoint `/outcomes/<id>/mark-nci`)
- `templates/audit_clo.html` (add NCI button and modal)
- `static/audit_clo.js` (NCI confirmation logic)
- `dashboard_service.py` (update stats to exclude NCI from pending)
- `tests/unit/test_clo_workflow_service.py` (test NCI status)
- `tests/e2e/test_uat_008_clo_approval_workflow.py` (add NCI scenario)

**Testing Requirements:**

- Unit tests for NCI status change
- Integration tests for dashboard stats
- E2E test for full NCI workflow
- Test filtering and visual indicators

---

### 3.2 Add Course Due Date Field

**Issue:** Leslie needs flexible deadlines per course (main campus vs. early college).

**Database Changes:**

```python
# Add to Course or Section model
class Course:
    # ... existing fields ...
    due_date: datetime  # NEW - When assessment is due
```

**UI Changes:**

**A. Import/Admin Interface:**

- Add due date field to course creation/edit forms
- Calendar date picker (HTML5 `<input type="date">`)
- Import adapter: Parse due_date from feed if present, otherwise default

**B. Instructor Dashboard:**

- Display due date prominently for each course
- Sort/filter courses by due date
- Visual indicator for overdue courses (red)
- Visual indicator for upcoming deadlines (yellow within 7 days)

**C. Reminder Emails:**

- Use course-specific due date in email template
- "Your assessment for {{ course.course_number }} is due {{ course.due_date | date_format }}"

**Affected Files:**

- `models.py` (add `due_date` field)
- `adapters/cei_excel_adapter.py` (parse due_date if present in feed)
- `templates/institution_dashboard.html` (show due date, sorting)
- `static/institution_dashboard.js` (filtering by due date)
- `templates/instructor_dashboard.html` (show due date for each course)
- `templates/emails/course_reminder.html` (use course.due_date)
- `bulk_email_service.py` (pass due_date to email template)
- `scripts/seed_db.py` (populate due_date for seed data)

**Affected Workflows:**

- Bulk reminder sending: Filter by due date range
- Dashboard filtering: "Due this week", "Overdue", "Due by date"
- Reporting: Group by due date

**Testing Requirements:**

- Unit tests for due date parsing in import
- Integration tests for dashboard filtering
- E2E test for due date display and sorting
- Test reminder email with course-specific date

---

## Phase 4: Polish and Testing (Week 7-8)

### 4.1 Email Deep Link Fix (LOW Priority)

**Issue:** Reminder email link doesn't take instructor directly to assessment page.

**Current Behavior:** Link goes to dashboard, instructor must navigate to assessment manually.

**Required Behavior:** Link goes directly to assessment page, auto-login if session exists.

**Implementation:**

- Generate course-specific URL with auth token or session validation
- Update email template with deep link
- Add server-side route to validate token and redirect

**Affected Files:**

- `bulk_email_service.py` (generate deep link URL)
- `templates/emails/course_reminder.html` (update link)
- `api_routes.py` or new route (handle deep link redirect)
- `tests/integration/test_email_service.py` (test link generation)

---

### 4.2 Comprehensive Testing and Documentation

**Testing Checklist:**

- [ ] All unit tests pass (Python)
- [ ] All unit tests pass (JavaScript)
- [ ] All integration tests pass
- [ ] All E2E tests pass (UAT suite)
- [ ] Manual testing of critical paths:
  - [ ] Import course data
  - [ ] Assign instructor
  - [ ] Instructor completes assessment (new workflow)
  - [ ] Admin reviews and approves
  - [ ] Admin marks as NCI
  - [ ] Export data
- [ ] Regression testing:
  - [ ] Existing features still work
  - [ ] No performance degradation

**Documentation Updates:**

- [ ] Update user stories to reflect new workflow
- [ ] Update API documentation
- [ ] Update database schema documentation
- [ ] Create admin guide for NCI status
- [ ] Create instructor guide for new assessment entry
- [ ] Update import format documentation (if due_date added)

---

## Implementation Sequence and Dependencies

### Week 1-2: Database Foundation

```
Day 1-2:  Design new schema (models.py updates)
Day 3-4:  Update database access layer (database_sqlite.py, database_service.py)
Day 5-6:  Update seed script for new schema
Day 7-8:  Nuke databases, reseed, write unit tests
Day 9-10: Test new schema with sample data, fix issues
```

**Blockers:** None - can start immediately

**Deliverable:** Updated schema with clean databases and passing tests

---

### Week 3-4: UI Redesign

```
Day 1-2:  Update assessments.html template
Day 3-4:  Update JavaScript validation
Day 5-7:  Update API endpoints
Day 8-10: Write and run E2E tests
```

**Dependencies:** Phase 1 complete (database schema)

**Deliverable:** Working instructor assessment entry with new workflow

---

### Week 5-6: Audit Enhancements

```
Day 1-2:  Implement NCI status (backend)
Day 3-4:  Update audit UI for NCI
Day 5-6:  Implement due date field
Day 7-8:  Update dashboards and filtering
Day 9-10: Write and run tests
```

**Dependencies:** Phase 2 complete (data entry working)

**Deliverable:** Admin can mark NCI, courses have due dates

---

### Week 7-8: Polish and Testing

```
Day 1-2:  Fix email deep link
Day 3-5:  Comprehensive testing (all layers)
Day 6-8:  Documentation updates
Day 9-10: Code review and refinement
```

**Dependencies:** Phases 1-3 complete

**Deliverable:** Production-ready system for UAT handoff

---

## Risk Mitigation

### High-Risk Areas

**1. Database Schema Changes (Phase 1)**

- **Risk:** Breaking existing test data, seed scripts need updating
- **Mitigation:**
  - Greenfield advantage: Just nuke and rebuild databases
  - Update seed scripts to match new schema
  - Update all test fixtures
  - No production data exists yet, so no migration concerns

**2. UI Workflow Change (Phase 2)**

- **Risk:** Breaking existing instructor workflow, user confusion
- **Mitigation:**
  - Extensive E2E testing before UAT
  - Prepare user training materials
  - Implement gradual rollout if possible
  - Have rollback plan

**3. Validation Logic Complexity (Phase 2)**

- **Risk:** Edge cases in enrollment reconciliation, validation bugs
- **Mitigation:**
  - Comprehensive unit test suite (20+ scenarios)
  - Real-world test data from Leslie
  - cannot_reconcile escape hatch for edge cases

### Medium-Risk Areas

**4. Timeline Pressure**

- **Risk:** 8 weeks is aggressive for this scope
- **Mitigation:**
  - Phase 4 (polish) can slip slightly if needed
  - Email deep link (4.1) can be deferred to post-UAT
  - Focus on CRITICAL items first

**5. Requirements Clarification**

- **Risk:** Misunderstanding Leslie's requirements
- **Mitigation:**
  - Schedule mid-implementation check-in (end of Week 4)
  - Show working demo of Phase 2 before proceeding to Phase 3
  - Keep communication channel open for questions

---

## Success Criteria

### Phase 1 Success

- [ ] Schema updated in models.py
- [ ] Seed script updated for new schema
- [ ] Databases nuked and recreated successfully
- [ ] Sample data validates correctly with new schema
- [ ] All unit tests pass with new schema

### Phase 2 Success

- [ ] Instructor can complete assessment using new workflow
- [ ] All validation rules work correctly
- [ ] Cannot_reconcile bypass works as expected
- [ ] E2E tests pass

### Phase 3 Success

- [ ] Admin can mark submissions as NCI
- [ ] Dashboard stats correctly exclude NCI from pending
- [ ] Due dates display and filter correctly
- [ ] Reminder emails use course-specific dates

### Phase 4 Success

- [ ] All tests pass (unit, integration, E2E)
- [ ] Documentation complete
- [ ] System ready for UAT handoff

### Overall Success

- [ ] Leslie approves the updated workflow in UAT
- [ ] No critical bugs found
- [ ] Performance acceptable
- [ ] Ready for Spring 2026 go-live

---

## Appendix A: File Impact Analysis

### High-Impact Files (Major Changes Required)

- `models.py` / `models_sql.py` - Core data model changes
- `templates/assessments.html` - Complete UI restructure
- `static/assessments.js` - New validation logic
- `database_sqlite.py` - Query updates for new schema
- `clo_workflow_service.py` - NCI status logic

### Medium-Impact Files (Moderate Changes)

- `api_routes.py` or `api/routes/*.py` - Update API endpoints
- `dashboard_service.py` - Stats calculation changes
- `bulk_email_service.py` - Due date in emails
- `adapters/cei_excel_adapter.py` - Parse due_date
- Migration scripts (new)

### Low-Impact Files (Minor Changes)

- `templates/audit_clo.html` - Add NCI button
- `templates/instructor_dashboard.html` - Show due date
- `static/audit_clo.js` - NCI confirmation
- Email templates - Update copy

### Test Files (All Require Updates)

- `tests/unit/test_*` (Python unit tests)
- `tests/javascript/unit/*.test.js` (JavaScript unit tests)
- `tests/integration/test_*` (Integration tests)
- `tests/e2e/test_uat_*.py` (E2E tests)

---

## Appendix B: Validation Rules Summary

### CLO Assessment Validation

```python
def validate_clo_assessment(students_took, students_passed, enrollment):
    if students_took > enrollment:
        raise ValidationError("Students who took assessment cannot exceed enrollment")
    if students_passed > students_took:
        raise ValidationError("Students who passed cannot exceed those who took assessment")
    if students_took < 0 or students_passed < 0:
        raise ValidationError("Values cannot be negative")
    return True
```

### Course Enrollment Validation

```python
def validate_course_enrollment(enrollment, withdrawals, passed, dfic, cannot_reconcile):
    expected = enrollment - withdrawals
    actual = passed + dfic

    if cannot_reconcile:
        return True  # Bypass validation

    if actual != expected:
        raise ValidationError(
            f"Enrollment reconciliation failed: {passed} passed + {dfic} DFIC = {actual}, "
            f"but expected {enrollment} enrollment - {withdrawals} withdrawals = {expected}. "
            f"Check 'Cannot Reconcile' if numbers don't match."
        )

    return True
```

---

## Appendix C: UAT Handoff Checklist

Before handing off to Leslie and Matt for UAT:

### Functional Completeness

- [ ] All CRITICAL items implemented
- [ ] All HIGH items implemented
- [ ] LOW items implemented or documented as deferred

### Quality Gates

- [ ] All unit tests pass (Python + JavaScript)
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Code review complete
- [ ] No critical SonarCloud issues
- [ ] Coverage >= 80%

### Documentation

- [ ] User guide for instructors (assessment entry)
- [ ] User guide for admins (NCI status, due dates)
- [ ] API documentation updated
- [ ] Database schema documented
- [ ] Known issues documented

### Environment Setup

- [ ] UAT environment deployed
- [ ] Sample data loaded
- [ ] Test accounts created (Leslie, Matt, sample instructors)
- [ ] Email delivery working (not test mode)

### Training and Support

- [ ] Schedule UAT kickoff meeting
- [ ] Provide walkthrough of new features
- [ ] Establish support channel (email, Slack, etc.)
- [ ] Set expectations for feedback turnaround

---

**Ready to implement? Let's start with Phase 1: Database Schema Redesign!**
