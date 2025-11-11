# Single Term Outcome Management Demo

**Duration:** 30 minutes  
**Year:** 2025  
**Workflow:** Import course data → Assign instructors → Complete assessments → Audit/approve → Export results

---

## Setup

```bash
# Navigate to project
cd /path/to/course_record_updater

# Activate environment
source venv/bin/activate

# Seed demo database (clears existing data)
python scripts/seed_db.py --demo --clear --env dev

# Start server
./restart_server.sh dev
```

**Demo Account:**
- URL: http://localhost:3001
- Email: demo2025.admin@example.com  
- Password: Demo2024!

---

## Demo Flow

### Step 1: Login

Navigate to http://localhost:3001. You'll see the login page with email and password fields.

Enter the credentials above and click "Sign In".

You should be redirected to the Institution Admin Dashboard showing Demo University.

**Press Enter to continue →**

---

### Step 2: Import Course Data

From the dashboard sidebar, click "Import Data".

The import page loads with a file upload interface.

Select import format: "Generic CSV Format" from the dropdown.

Click "Choose File" and select a CSV file with course data.

Click "Import" button (green).

Progress indicator appears, then success message: "Import completed".

Dashboard refreshes automatically showing 4-5 new course sections with status "Unassigned".

**Press Enter to continue →**

---

### Step 3: Assign Instructor

From the Course Sections Dashboard, locate a course (e.g., CS-101).

Click "Assign Instructor" button on that row.

A modal opens: "Assign Instructor to CS-101"

Choose "Create New Instructor" option.

Fill in:
- First Name: Demo
- Last Name: Instructor  
- Email: demo2025.instructor@example.com (or your real email to test)

Click "Assign and Invite" button.

Success message appears: "Instructor assigned and invitation sent"

Course status changes to "Assigned".

If you used a real email, check it - you should receive an invitation within 30-60 seconds.

**Press Enter to continue →**

---

### Step 4: Instructor Registration (Instructor View)

Open the invitation email and click the link, OR navigate to the registration page manually.

Registration page loads: "You've been invited to complete learning outcomes for CS-101"

Email field is pre-filled: demo2025.instructor@example.com

Enter password: Demo2024! (twice)

Click "Complete Registration"

System auto-logs in and redirects to CS-101 assessment page.

**Press Enter to continue →**

---

### Step 5: Complete Assessment (Instructor View)

Assessment page title: "CS-101: Introduction to Programming - Fall 2025"

**Course-Level Section (top):**
- Enrollment: 25 (pre-populated, read-only)
- Withdrawals: 2 (pre-populated, read-only)
- Enter students passed (A/B/C): 20
- Enter students DFIC (D/F/Incomplete): 3
- System validates: 20 + 3 = 23 = 25 - 2 ✓

**CLO Assessment Section:**
For each CLO (3-5 listed):
- Assessment Tool: "Midterm Exam"
- Students took: 23
- Students passed: 20  
- Auto-calculated pass rate displays: ~87%

**Course Narratives:**
- Celebrations: "Students showed strong understanding of fundamentals."
- Challenges: "Debugging skills need emphasis."
- Changes: "Add more pair programming exercises."

Click "Submit for Approval" button at bottom.

Confirmation: "Are you sure?" → Click "Yes, Submit"

Success message: "Assessment submitted for approval"

Status badge changes to "Awaiting Approval"

Submit button is now disabled.

**Press Enter to continue →**

---

### Step 6: Admin Review (Admin View)

Switch back to admin browser tab (or login as demo2025.admin@example.com again).

Refresh the dashboard (F5).

CS-101 status now shows "Awaiting Approval" with yellow/orange badge.

Click "CLO Audit" in left sidebar.

Audit dashboard loads with summary stats:
- Awaiting Approval: 1 (or more)
- Approved: X
- Needs Rework: 0

Table shows CS-101 row with instructor name, submission date, status.

Click "Review" button on CS-101 row.

**Press Enter to continue →**

---

### Step 7: Audit Detail Modal

Modal opens: "CLO Audit Details"

Shows complete submission:
- Course: CS-101, Fall 2025
- Instructor: Demo Instructor
- Enrollment: 25, Withdrawals: 2, Passed: 20, DFIC: 3
- All CLO assessments with tools and pass rates
- Complete narratives (celebrations, challenges, changes)
- Submission timestamp

Three action buttons at bottom:
- **Approve** (green) - Accept submission
- **Request Rework** (yellow) - Send back with feedback
- **Mark as Never Coming In** (gray) - Close out non-responsive

Click "Approve" button.

Confirmation: "Are you sure?" → Click "Yes, Approve"

Success message: "Assessment approved successfully"

Modal closes automatically.

Table updates: CS-101 status → "Approved" (green badge)

Summary stats update: Approved count increases, Awaiting decreases.

**Press Enter to continue →**

---

### Step 8: Export

Click "Export Data" in sidebar.

Export page loads with filters:
- Term: Fall 2025 (selected)
- Program: All
- Status: Approved Only (default)

Table shows approved courses ready for export.

CS-101 appears with checkbox and "Ready for Export" status.

Check the box next to CS-101 (or multiple courses).

Click "Mark Selected for Export" button.

Click "Export to CSV" (or "Export to Excel") button.

File downloads: `learning_outcomes_fall2025.csv`

Open the file to verify:
- Columns: Course, Instructor, CLO Number, Description, Assessment Tool, Students Took, Students Passed, Pass Rate, Narratives, etc.
- CS-101 data is present with all details

Return to export page (refresh).

CS-101 now shows "Exported" status with timestamp.

Checkbox is disabled (prevents duplicate export).

**Press Enter to continue →**

---

## Demo Complete

You've walked through the complete single-term outcome management workflow:
1. ✅ Import course data from feed
2. ✅ Assign instructor to course
3. ✅ Instructor registers and completes assessment
4. ✅ Admin reviews and approves submission
5. ✅ Export approved data for reporting

---

## Key Features Demonstrated

- **Import**: Multiple format support (CSV, Excel, custom)
- **Assignment**: Create instructors on-the-fly with email invitations
- **Assessment**: CLO-level tracking with course-level narratives
- **Validation**: Real-time checks (enrollment reconciliation, pass rates)
- **Audit**: Quality control with approve/rework/NCI options
- **Export**: Track what's been exported, prevent duplicates

---

## Follow-Up Questions

**Q: Can I remind multiple instructors at once?**  
A: Yes, bulk reminder feature lets you select courses and send batch emails.

**Q: What if an instructor makes a mistake after submitting?**  
A: Admin sends it back with "Request Rework". Instructor gets notification, makes corrections, resubmits.

**Q: What happens if an instructor leaves mid-term?**  
A: Reassign to a different instructor, OR mark as "Never Coming In" (NCI) to close it out.

**Q: Can I set different deadlines per course?**  
A: Yes, each course can have its own due date (handles early college vs. main campus).

**Q: How reliable is email delivery?**  
A: Uses professional providers (Brevo, etc.) with high deliverability. Email status tracked in admin dashboard.

---

## Notes for Presenter

- **Pacing**: Don't rush the import - explain what's happening
- **Highlight**: Instructor flow is the "wow moment" - make it smooth  
- **Show Value**: Admin audit demonstrates quality control
- **Close Loop**: Export shows bi-directional data flow

**Common Pitfalls:**
- Email delays (30-60s) - have backup tab ready
- Browser caching - refresh liberally
- Forgot to reseed - always start fresh

---

**Demo Script Version:** 2025.1  
**Last Updated:** November 11, 2025

