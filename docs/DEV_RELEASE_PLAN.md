# Dev Release Plan v3

**Goal:** Ship a `.dev` site that Leslie and Matthew can use to validate the core data flow.

---

## 🍷 Tyrion's Framing

The real question is: **what is the minimum bar for Leslie and Matthew to meaningfully test the system?**

They need:

1. To log in (and reset their password if forgotten).
2. To see data that looks real.
3. To complete the Import → Assign → Assess → Approve → Export loop.
4. To review audit logs for compliance validation.
5. To not hit a "TODO" error or dead button.

---

## Phase 1: Achieve "No Dead Ends"

**Objective:** Every button does something. Every flow reaches a conclusion.

### Blocking TODOs to Fix

| File                    | TODO                   | Required Action                         |
| ----------------------- | ---------------------- | --------------------------------------- |
| `panels.js:983`         | Audit log viewer       | **Implement** - required for compliance |
| `panels.js:993`         | Filter modal           | **Implement** - part of audit UX        |
| `auth.js:705`           | Profile update         | **Implement**                           |
| `auth.js:710`           | Password change        | **Implement** - required for pilot      |
| `import_service.py:572` | `update_course`        | **Implement** for re-import support     |
| `import_service.py:792` | Offering creation stub | **Implement** - blocker                 |
| `import_service.py:816` | Section creation stub  | **Implement** - blocker                 |
| `import_cli.py:299`     | Validation-only mode   | **Implement** for import safety         |

### Invitation Flow Validation (REQUIRED)

> Don't ship until you've manually walked the invitation path once.

- [ ] Admin invites instructor via UI
- [ ] Email arrives (check Ethereal/Brevo logs)
- [ ] Instructor clicks link and registers
- [ ] Instructor logs in successfully
- [ ] Instructor sees their dashboard with assigned sections

**Note:** `test_email_flows_registration.py` is currently a stub (545 lines of `pass`). Either implement real tests or manually verify before release.

### Acceptance Criteria

- [ ] Run the 8-step demo walkthrough. Zero errors, zero console errors.
- [ ] All TODOs in the table above are resolved.
- [ ] Invitation flow manually verified end-to-end.

---

## Phase 2: Green CI & Merge to Main

**Objective:** All checks passing; feature branch merged; ready for automated deploy.

### CI Checks Required

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] E2E tests passing
- [ ] SonarCloud quality gate passed (or documented exceptions)
- [ ] No security vulnerabilities (Safety, Semgrep)

### Merge Process

- [ ] Open PR from `feat/finalize_dev_release` → `main`
- [ ] All CI checks green
- [ ] PR approved and merged
- [ ] Verify `main` branch is stable post-merge

---

## Phase 3: Deploy via GitHub Actions

**Objective:** Use the automated workflow to deploy `main` to dev environment.

- [ ] Trigger the "Deploy to Cloud Run" workflow from GitHub Actions
- [ ] Select `dev` environment
- [ ] Confirm deployment succeeds
- [ ] Run `python demos/run_demo.py --env development` against deployed site
- [ ] Confirm all demo steps pass
- [ ] Note any data tweaks needed (owner will adjust dataset as needed during validation)

---

## Phase 4: DNS & Access

**Objective:** Professional URL; stakeholders can reach the site.

- [ ] Create Cloud Run domain mapping for `dev.loopcloser.io`
- [ ] Configure Cloudflare CNAME record
- [ ] Verify HTTPS works
- [ ] Verify email delivery (invitations, reminders)

---

## Phase 5: Finalize & Record

**Objective:** Prepare all handoff materials.

### Seeding Data

- [ ] Finalize demo dataset (adjust during validation runs)
- [ ] Ensure "Demo University" has realistic programs/courses/sections

### Demo Video

- [ ] Record Loom/video walkthrough of the full demo flow
- [ ] Cover: Login → Import → Assign → Assess → Approve → Export
- [ ] Highlight areas for feedback

### Credentials & Instructions

- [ ] Document login credentials for test accounts
- [ ] Write clear instructions for accessing `dev.loopcloser.io`
- [ ] Include which browser to use, if relevant

### Questionnaire

Prepare questions for Leslie and Matthew to validate:

- [ ] Can you log in with provided credentials?
- [ ] Can you import sample course data?
- [ ] Can you assign an instructor to a section?
- [ ] Can an instructor submit assessment data?
- [ ] Can you approve submitted assessments?
- [ ] Can you export the final data?
- [ ] Can you view the audit log of actions taken?
- [ ] Can you reset a forgotten password?
- [ ] What friction points or confusion did you encounter?
- [ ] What is missing for your actual workflow?

---

## Phase 6: Handoff

**Objective:** Leslie and Matthew begin testing.

- [ ] Deliver credentials, URL, and video
- [ ] Share questionnaire
- [ ] Set 1-week feedback window
- [ ] Schedule debrief call

---

## Out of Scope for Dev Release

- CEI-specific import adapter (Phase 2 work after validation)
- Production DNS and data migration

---

## Key Milestones

| Phase | Milestone                            | Target |
| ----- | ------------------------------------ | ------ |
| 1     | "No Dead Ends" + Invitation verified | TBD    |
| 2     | CI green, merged to main             | TBD    |
| 3     | Deployed via Actions, demo passes    | TBD    |
| 4     | DNS live                             | TBD    |
| 5     | Video recorded, materials ready      | TBD    |
| 6     | Handoff complete                     | TBD    |
