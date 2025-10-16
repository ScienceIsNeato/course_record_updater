# Program Administrator User Stories

**Context:** Managing instructor workflow and CLO assessment data collection
**Primary Goal:** "Push out the data and pull it back" - coordinate assignments and data collection

---

## Feed Management

### 1. Upload Assessment Feed
**As a program administrator, I want to** upload a .xlsx or .csv feed file to initialize the assessment process for the semester **so that** all course-instructor combinations and CLLOs are automatically populated in the system.

## Managing Instructors

### 2. View Main Course Sections Dashboard
**As a program administrator, I want to** view the main dashboard showing all course sections with status indicators (Unassigned, Assigned, Editing, Complete, Overdue) and filters for year, term, instructor, and status **so that** I can quickly identify which sections need attention and hone in on specific subsets of my course portfolio.

### 3. View Users Dashboard
**As a program administrator, I want to** view all instructors with their active and completed course sections **so that** I can see which instructors are assigned to which courses and track their submission status.

### 4. Add Existing Instructor to Course Section
**As a program administrator, I want to** select an existing instructor from a dropdown and assign them to a course section **so that** I can connect instructors to the course sections they are teaching.

### 5. Add New Instructor to Course Section
**As a program administrator, I want to** create a new instructor (name + email) and assign them to a course section in one dialog **so that** I can staff sections with new faculty without having to create their account separately first.

### 6. Generate and Send Instructor Invitation
**As a program administrator, I want to** generate an invitation email for an assigned instructor **so that** they remockuve clear instructions on how to access their course section and complete assessment data.

### 7. Remove Instructor from Course Section
**As a program administrator, I want to** remove an instructor from a course section **so that** I can handle staffing changes, emergency reassignments, or instructor withdrawals.

### 8. Track Instructor Invitation Status
**As a program administrator, I want to** see the status of instructor invitations (Invited, Accepted) per course section **so that** I know which instructors have engaged with the system and which need follow-up.

### 9. Send Bulk Reminders to Incomplete Instructors
**As a program administrator, I want to** filter to see current term instructors who haven't submitted and send them all a reminder with a single button click **so that** I can efficiently follow up with multiple instructors at once.

---

## Quality Assurance & Audit

### 10. Access Course Section as Instructor
**As a program administrator, I want to** view any course-instructor combination exactly as the assigned instructor sees it **so that** I can spot check that the feed has loaded correctly prior to sending links out and provide support as needed.

### 11. Quality Audit Process
**As a program administrator, I want to** mark each submitted rubric with audit status checkboxes (imported, quality checked, remediate, NCI) **so that** I can track the quality review process and determine which records are ready for export.

### 12. Mark Ready for Export
**As a program administrator, I want to** mark audited rubrics as "ready for export" **so that** I can control exactly which records will be included in the export file and ensure data quality.

## Communication & Notifications

### 13. Configure Notification Templates
**As a program administrator, I want to** edit notification message templates with course-specific variables (course name, deadline, etc.) **so that** instructors remockuve personalized, relevant reminders about their specific assignments.

### 14. Set Notification Timing
**As a program administrator, I want to** configure how many days before the term deadline notifications are sent and what time of day **so that** instructors remockuve reminders at the most effective times for completion.

### 15. View Scheduled Notifications
**As a program administrator, I want to** see all upcoming scheduled notifications in a dashboard **so that** I can monitor what communications are planned and make adjustments if needed.

### 16. Send Immediate Notification
**As a program administrator, I want to** send a notification immediately instead of waiting for the scheduled time **so that** I can provide urgent reminders or updates to instructors.

### 17. Resend Previous Notification
**As a program administrator, I want to** resend a notification that was already sent **so that** I can follow up with instructors who may have missed or ignored the original message.

---

## Data Export & Management

### 20. Create New Course Template
**As a program administrator, I want to** create a new course (like "Accounting 101") with CLO templates **so that** I can establish the assessment structure that will be used across all sections of that course.

### 21. Create Course Section
**As a program administrator, I want to** create a course section under an existing course with specific term and year **so that** instructors can be assigned to teach specific instances of the course.

### 22. Manage Terms and Years
**As a program administrator, I want to** add and edit academic terms and years in a dedicated management view **so that** I can maintain the academic calendar structure for course section creation.

### 23. Manage Course Learning Outcomes (CLOs)
**As a program administrator, I want to** add, edit, and organize CLOs in a dedicated management view **so that** I can create a library of learning outcomes to assign to courses.

### 24. Assign CLOs to Courses
**As a program administrator, I want to** select CLOs from a dropdown and assign them to courses **so that** I can reuse standardized learning outcomes across multiple course sections without recreating them.

### 25. Edit Course Section Data as Instructor
**As a program administrator, I want to** edit enrollment numbers, CLO assessments, and narratives for any course section **so that** I can make corrections or complete data entry when instructors are unavailable.

### 18. Export Course Data
**As a program administrator, I want to** export data marked as "ready for export" in .xlsx/.csv format, and have those records automatically marked as "exported" to prevent duplicate exports **so that** I can integrate with existing institutional workflows without data duplication.

### 19. Clear Exported Data
**As a program administrator, I want to** clear exported data when the assessment process is complete and prepare the system for the next semester's feed **so that** the system is ready for new assessment cycles, understanding that some courses may have holdover rubrics into subsequent terms.

---

## Course & CLO Management
