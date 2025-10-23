# Learning Outcomes Demo - Meeting Outline
**Date:** Friday, October 24, 2024  
**Time:** 1:00 - 1:30pm  
**Attendees:** Leslie Jernberg, Matthew Taylor, Will Martin

---

## Meeting Structure (30 minutes)

### Part 1: PowerPoint Overview (5 minutes)

**Slides to prepare:**
1. Project status recap
2. What we've built (high-level feature list)
3. What's in scope for this demo
4. What's NOT in scope yet (the "great features" for later)
5. Today's goal: Validate the core workflow

### Part 2: Live Demo - "The Middle Workflow" (10 minutes)

**Demo Setup:**
- Fresh database with ONLY Leslie's account pre-seeded
- Local dev server running (port 3001)
- 2024FA test data file ready to upload
- Mailtrap configured for email capture
- You drive everything; Leslie and Matt observe

**Demo Flow:**

#### Scene 1: Import the Feed (2 min)
- Login as Leslie (program admin)
- Navigate to import interface
- Upload 2024FA.xlsx (Matt: BIOL-228 + ZOOL-127, Leslie: 2 classes)
- Show automatic parsing and course section creation
- View dashboard with 4 new course sections

#### Scene 2: Invite Instructors (2 min)
- Assign Matt to BIOL-228 and ZOOL-127
- Generate invitation emails
- Show Mailtrap inbox with invitation emails
- Highlight: One email per course assignment

#### Scene 3: Instructor Completes Rubric (2 min)
- Click invitation link (opens registration)
- Register Matt as instructor
- Navigate to BIOL-228 rubric
- Fill in enrollment numbers and CLO ratings
- Add narrative comments
- Submit for approval

#### Scene 4: Admin Tracking & Audit (3 min)
- Back to Leslie's dashboard
- Show completion status tracking
- Navigate to CLO Audit interface
- Review Matt's submitted rubric
- Demonstrate approval action
- Show audit trail preservation

#### Scene 5: Export (1 min)
- Mark approved rubric as "ready for export"
- Generate export file
- Show export format
- Highlight: Automatic "exported" flag prevents duplicates

### Part 3: Feedback & Q&A (10 minutes)

**Key question:** "Is this the workflow you need?"

**Anticipated questions:**
- Bulk reminders: "How do I remind multiple instructors at once?"
- Filtering: "Can I filter by term/status/instructor?"
- Corrections: "What if I need to fix data after submission?"
- Reassignments: "What if an instructor changes mid-term?"
- Timeline: "When can we use this with real data?"

### Part 4: Next Steps (5 minutes)

**Discuss:**
- Feedback incorporation timeline
- UAT testing with real CEI data
- Training plan
- Production deployment target
- Next demo (deployed version, let them drive)

---

## Technical Prep Checklist

**Pre-Demo Setup:**
- [ ] Create fresh dev database
- [ ] Seed Leslie's account (see curl command below)
- [ ] Start local server: `./restart_server.sh`
- [ ] Verify Mailtrap is configured and accessible
- [ ] Have 2024FA.xlsx test file ready
- [ ] Clear browser cache/session
- [ ] Have PowerPoint slides prepared
- [ ] Test full workflow once as rehearsal

**Leslie Account Creation:**
```bash
# Create Leslie as program admin at CEI
curl -X POST http://localhost:3001/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "leslie.jernberg@cei.edu",
    "password": "TempDemo123!",
    "name": "Leslie Jernberg",
    "role": "program_admin",
    "institution_id": "cei"
  }'
```

**Note:** Adjust endpoint/auth if needed based on current API implementation.

---

## Known Limitations to Mention

**Out of scope for initial release:**
- Notification timing configuration
- Course/CLO template management
- Term/year management interface
- Some advanced filtering options

**Still need CEI input:**
- Final export format specifications
- Integration points with institutional systems
- Production hosting preferences

---

## Success Criteria

Demo is successful if:
- Leslie confirms this matches her workflow vision
- Leslie and Matt identify any critical missing pieces
- We get actionable feedback on UI/UX improvements
- We align on next steps and timeline

---

## Notes & Action Items

*(To be filled in during/after the meeting)*

**Feedback received:**

**Action items:**

**Follow-up questions:**

