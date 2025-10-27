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
- Email provider configured for REAL email delivery to unique.will.martin@gmail.com
- You drive everything; Leslie and Matt observe

**Demo Flow:**

#### Step 0: Seed Demo Database (DO THIS FIRST!)

**EXACT STEPS:**

1. **Open Terminal**
2. **Navigate to project:**
   ```bash
   cd /Users/pacey/Documents/SourceCode/course_record_updater
   ```
3. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```
4. **Clear and seed demo database:**
   ```bash
   python scripts/seed_db.py --cei-demo --clear --env dev
   ```
5. **Verify success:**
   - Look for: `[SEED] 🗄️  Using dev database: course_records_dev.db`
   - Look for: `✅ CEI demo seeding completed!`
   - Confirm Leslie's credentials shown: `leslie.jernberg@cei.edu` / `Demo2024!`
6. **Start server:**
   ```bash
   ./restart_server.sh dev
   ```
7. **Verify server running:**
   - Look for: `Running on http://127.0.0.1:3001`

**CRITICAL:** This creates a clean, deterministic demo environment. Run this before EVERY demo rehearsal.

---

#### Scene 1: Import the Feed (2 min)

**EXACT STEPS:**

1. **Open browser** → Navigate to `http://localhost:3001`
2. **Login page** appears
   - Enter email: `leslie.jernberg@cei.edu`
   - Enter password: `Demo2024!`
   - Click **"Sign In"** button
3. **Institution Admin Dashboard** loads
   - Point out: "This is Leslie's main dashboard as an institution administrator"
   - Note the navigation menu on the left
4. **Navigate to Import**
   - Click **"Import Data"** in the left sidebar (or find Import link in navigation)
   - Import page loads with file upload interface
5. **Select Import Format**
   - In the **"Import Format"** dropdown, select: **"CEI Excel Format v1.2"**
   - This tells the system which adapter to use for parsing the file
6. **Upload File**
   - Click **"Choose File"** button or drag-and-drop area
   - Select file: `research/CEI/2024FA_test_data.xlsx`
   - File name appears next to "Choose File" button
7. **Start Import**
   - Click **"Excel Import"** button (large green button)
8. **Watch Processing**
   - Progress indicator appears
   - Success message: "Import completed"
   - Import Results section shows success details
9. **View Results**
   - **Page automatically reloads after 2 seconds** to show updated data
   - Dashboard shows 4 new course sections:
     - BIOL-228 (assigned to Matt in feed)
     - ZOOL-127 (assigned to Matt in feed)
     - Plus 2 more for Leslie
   - Status shows "Unassigned" for all
   - **Program Management panel automatically shows correct counts** (courses are auto-linked to programs during import)

**TALKING POINT:** "Notice how the system automatically parsed the Excel file and created all course sections with their CLOs. This is the exact feed format you provided. The Program Management panel shows accurate counts across all programs - the system automatically links courses to the appropriate programs based on their course numbers."

---

#### Scene 2: Invite Instructor (Semester Change Scenario) (2 min)

**SCENARIO:** "Matt Taylor taught BIOL-228 last semester, but Will Martin is taking over this semester. This demonstrates how you handle instructor changes between terms."

**EXACT STEPS:**

1. **From Course Sections Dashboard**
   - Locate **BIOL-228** row in the table
   - Click **"Assign Instructor"** button (or "Actions" → "Assign")
2. **Assign Instructor Modal Opens**
   - Modal title: "Assign Instructor to BIOL-228"
   - **Option 1:** Select existing instructor (dropdown)
   - **Option 2:** Create new instructor (form fields)
3. **Create Will's Account (New Instructor)**
   - Choose "Create New Instructor" option
   - Fill in form:
     - First Name: `Will`
     - Last Name: `Martin`
     - Email: `unique.will.martin@gmail.com`
   - Click **"Assign and Invite"** button
4. **Confirmation**
   - Success message: "Instructor assigned and invitation sent"
   - BIOL-228 status changes to "Assigned"
5. **Check REAL Email**
   - Pull up Gmail on phone or in separate browser tab
   - Navigate to `unique.will.martin@gmail.com` inbox
   - Show invitation email arrived (may take 10-30 seconds)
   - Open email to show content
   - Point out:
     - Professional email formatting
     - Course-specific subject line
     - Invitation link is unique to BIOL-228
     - Personal message from Leslie (if included)

**TALKING POINT:** "Notice this is a real email, not a test environment. The instructor receives a professional invitation with all the context they need - which course, who invited them, and what they need to do."

---

#### Scene 3: Instructor Registration & Rubric Completion (2 min)

**EXACT STEPS:**

1. **Click Invitation Link**
   - In Gmail, click the invitation link in the BIOL-228 email
   - Opens in new browser tab/window
2. **Registration Page Loads**
   - Shows: "You've been invited to complete learning outcomes for BIOL-228"
   - Shows inviter info: Leslie Jernberg, College of Eastern Idaho
   - Registration form appears
3. **Complete Registration**
   - Email field pre-filled: `unique.will.martin@gmail.com`
   - Enter password: `Demo2024!` (twice for confirmation)
   - Click **"Complete Registration"** button
4. **Auto-Login and Redirect**
   - System logs Will in automatically
   - Redirects directly to BIOL-228 rubric page
5. **Fill Out Rubric**
   - Page title: "BIOL-228: [Course Name] - Fall 2024"
   - **Enrollment section:**
     - Enter number: `24` (total enrollment)
   - **CLO Assessment section:**
     - For each CLO (3-5 listed):
       - Enter "Students Assessed": `24`
       - Enter "Students Met": `20`
       - Select rating from dropdown (e.g., "Met" or "Exceeded")
   - **Narrative section:**
     - Text box appears
     - Type: "Students demonstrated strong understanding of core concepts. Areas for improvement include..."
6. **Submit for Approval**
   - Scroll to bottom
   - Click **"Submit for Approval"** button
   - Confirmation modal: "Are you sure you want to submit?"
   - Click **"Yes, Submit"** button
7. **Confirmation**
   - Success message: "Rubric submitted for approval"
   - Page shows status badge: "Awaiting Approval"
   - **"Submit"** button is now disabled

**TALKING POINT:** "Will can now see the submission is complete and waiting for Leslie to review it. Notice how seamless this was - from email to completion in under 2 minutes."

---

#### Scene 4: Admin Tracking & Audit (3 min)

**EXACT STEPS:**

1. **Return to Leslie's Dashboard**
   - Switch back to Leslie's browser tab/window
   - Refresh page (F5 or reload button) to see Will's submission
2. **Course Sections Dashboard**
   - BIOL-228 status now shows: **"Complete"** or **"Awaiting Approval"**
   - Color-coded status badge (yellow/orange for awaiting)
3. **Navigate to CLO Audit**
   - Click **"CLO Audit"** in left sidebar
   - OR click **"Review Submissions"** button in audit panel on dashboard
4. **CLO Audit Page Loads**
   - Page title: "CLO Audit & Approval"
   - Summary stats cards at top:
     - **"Awaiting Approval": 1**
     - **"Needs Rework": 0**
     - **"Approved": 0**
     - **"In Progress": X**
   - Filter dropdowns: Status, Program, Term
5. **View Submitted Rubrics**
   - Table shows list of CLOs awaiting review
   - Locate BIOL-228 row
   - Shows: Course, Instructor (**Will Martin**), Submitted Date, Status
6. **Review Details**
   - Click **"Review"** button or **"View Details"** link on BIOL-228 row
   - Modal opens: "CLO Audit Details"
7. **Audit Modal Content**
   - Shows full course information (BIOL-228)
   - Shows enrollment numbers (24 students)
   - Shows all CLO assessments with ratings
   - Shows narrative text (Will's comments)
   - Shows instructor name (**Will Martin**) and submission date
   - **Action buttons at bottom:**
     - **"Approve"** (green button)
     - **"Request Rework"** (yellow/orange button)
     - **"Cancel"**
8. **Approve the Rubric**
   - Review all data (narrate what you see)
   - Click **"Approve"** button
   - Confirmation: "Are you sure you want to approve this rubric?"
   - Click **"Yes, Approve"**
9. **Confirmation**
   - Success message: "Rubric approved successfully"
   - Modal closes
   - Table updates: BIOL-228 status now **"Approved"**
   - Summary stats update: **"Approved": 1**, **"Awaiting Approval": 0**

**TALKING POINT:** "Leslie can now track which rubrics have been submitted, review them for quality, and either approve them or send them back with feedback for corrections."

---

#### Scene 5: Export (1 min)

**EXACT STEPS:**

1. **Navigate to Export**
   - Click **"Export Data"** in left sidebar
   - Export page loads
2. **Export Page Interface**
   - Shows filters:
     - Term: **Fall 2024** (selected)
     - Program: **All** or specific
     - Status: **Approved Only** (selected by default)
   - Table shows approved rubrics ready for export:
     - BIOL-228 shows checkmark and **"Ready for Export"** status
3. **Mark Ready for Export** (if needed)
   - If not already marked, click checkbox next to BIOL-228
   - Click **"Mark Selected for Export"** button
4. **Generate Export File**
   - Click **"Export Selected to Excel"** button
   - File downloads: `cei_learning_outcomes_FA2024.xlsx`
5. **Show Export File**
   - Open downloaded file in Excel/Numbers
   - Show data structure:
     - Columns: Course, Instructor, CLO, Students Assessed, Students Met, Rating, Narrative, etc.
     - BIOL-228 data is present
   - Point out format matches CEI's requirements
6. **Automatic Status Update**
   - Return to export page (refresh)
   - BIOL-228 now shows status: **"Exported"**
   - Checkbox is disabled (prevents duplicate export)

**TALKING POINT:** "The system automatically tracks which rubrics have been exported to prevent duplicate data. You can run exports multiple times and only new data will be included."

### Part 3: Feedback & Q&A (10 minutes)

**Key question:** "Is this the workflow you need?"

**Anticipated questions:**
- Bulk reminders: "How do I remind multiple instructors at once?"
- Filtering: "Can I filter by term/status/instructor?"
- Corrections: "What if I need to fix data after submission?"
- Reassignments: "What if an instructor changes mid-term?" (Already demonstrated in Scene 2!)
- Timeline: "When can we use this with real data?"
- Email delivery: "How reliable is the email system?"
- Duplicate assignments: "What happens if I accidentally assign the same instructor twice?"

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
- [ ] Create fresh dev database and seed Leslie's account (run seed script)
- [ ] Start local server
- [ ] Verify email provider is configured for REAL email delivery (not Mailtrap)
- [ ] Confirm unique.will.martin@gmail.com can receive emails
- [ ] Have test file ready: research/CEI/2024FA_test_data.xlsx
- [ ] Have Gmail open on phone or separate browser tab
- [ ] Clear browser cache/session
- [ ] Have PowerPoint slides prepared
- [ ] Test full workflow once as rehearsal

**Database Setup Commands:**
```bash
# Navigate to project root
cd /Users/pacey/Documents/SourceCode/course_record_updater

# Activate virtual environment
source venv/bin/activate

# Clear and seed demo database
python scripts/seed_db.py --cei-demo --clear --env dev

# Start server
./restart_server.sh dev
```

**Demo Account Credentials:**
- Email: `leslie.jernberg@cei.edu`
- Password: `Demo2024!`

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

