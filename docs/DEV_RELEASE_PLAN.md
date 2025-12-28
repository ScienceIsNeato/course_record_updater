# Dev Release Implementation Plan

**Goal:** Prepare a polished `.dev` site for pilot partner validation before transitioning to production.

---

## Phase 1: Finalize Existing Website Flow
Ensure all currently-implemented features work end-to-end without dead buttons or broken paths.

- [ ] Audit all dashboard panels for placeholder/TODO functions
- [ ] Verify CLO Audit "Approve" button is connected to backend
- [ ] Confirm instructor invitation → registration → assessment flow
- [ ] Test export functionality produces valid CSV/Excel output

---

## Phase 2: Fix Dev Release Blocking Issues
Resolve all known blockers from the pre-release assessment.

- [ ] Fix `test_create_user_validation` assertion mismatch
- [ ] Address remaining uncovered NEW code (or document as accepted debt)
- [ ] Complete DNS mapping: `dev.loopcloser.io` → Cloud Run service
- [ ] Verify email delivery on `.dev` environment (Ethereal or Brevo)

---

## Phase 3: Finish Semester Demo Flow
Complete the [Single Term Outcome Management](docs/workflow-walkthroughs/single_term_outcome_management.md) workflow.

- [ ] Validate all 8 demo steps run cleanly on seeded data
- [ ] Ensure "Exported" status tracking prevents duplicate exports
- [ ] Test bulk reminder feature for instructors

---

## Phase 4: Mid-Semester Testbed for Leslie & Matthew
Create a stable, generic environment for internal stakeholders to validate the data flow. **No CEI branding.**

- [ ] Seed database with neutral "Demo University" institution
- [ ] Create test accounts for Leslie and Matthew
- [ ] Provide clear login credentials and starting point
- [ ] Document which workflows to exercise (Import, Assign, Assess, Approve, Export)

---

## Phase 5: Walkthrough Video
> **Owner:** Product Owner

- [ ] Record a video walkthrough of the `.dev` site
- [ ] Explain the intended user journey and data flow
- [ ] Highlight areas for feedback and experimentation

---

## Phase 6: CEI Evaluation Timeline
Define a window for pilot partner review before proceeding.

- [ ] Set evaluation start date (after video delivery)
- [ ] Define feedback collection method (form, email, call)
- [ ] Set a deadline for "Phase 6 Complete" (e.g., 1 week window)
- [ ] Schedule debrief call to discuss findings

---

## Phase 7: Final Validation with Real Data
Finalize the CEI-specific import adapter and allow partners to use their actual data on `.dev`.

- [ ] Complete CEI Excel adapter (if not already finalized)
- [ ] Provide a staging area or "sandbox" institution for their uploads
- [ ] Run validation-only mode before committing data
- [ ] Collect final sign-off on data accuracy and workflow fit

---

## Phase 8: Transition to Production
With `.dev` validated, prepare for the production release.

- [ ] Enable DNS for `loopcloser.io` (prod domain)
- [ ] Configure production email provider (Brevo)
- [ ] Migrate or re-seed production database
- [ ] Announce soft launch to pilot partners

---

## Key Milestones

| Phase | Milestone | Target Date |
|-------|-----------|-------------|
| 1-3 | Dev site "feature complete" | TBD |
| 4 | Internal testbed ready | TBD |
| 5 | Walkthrough video delivered | TBD |
| 6 | CEI evaluation window closes | TBD |
| 7 | Real data validation complete | TBD |
| 8 | Production launch | TBD |
