# CEI Demo Follow-ups

**Meeting Date:** October 24, 2025  
**Attendees:** Leslie Jernberg (Speaker 2), Matthew Taylor (Speaker 3), Will Martin (Speaker 1)  
**Source:** CEI_Demo_otter_ai.txt

---

## Executive Summary

The demo was well-received with Leslie confirming "Basically, yeah. I mean, it looks pretty close" (9:41). However, several critical functional gaps were identified that need to be addressed before the Spring 2026 launch (mid-April deadline). The feedback centered on three main areas: CLO assessment data collection, audit workflow enhancements, and export format requirements.

---

## Critical Functional Changes Required

### 1. CLO Assessment Data Entry - Students Took vs. Enrolled

**Quote (9:41-10:54):**

> "So it pre populated how many students were in the course, and so every student that's in the course does not necessarily take the assessment. Okay? Students literally don't show up for class, right? They don't show up for the test day. They don't show up the day that that thing is due. They don't turn it in. So the way that it's that I had it set up, is that the instructor would input how many students took the assessment, how many students passed the assessment? Okay, the percentage that matters, of course, the number of students that took the assessment can't exceed enrollment, right?"

**Follow-up Item 1.1: Modify CLO Assessment Data Model**

- **Current State:** System pre-populates enrollment and asks for "students passing"
- **Required State:**
  - Display enrollment as static, non-editable field (reference only)
  - Add field: "Number of students who took the assessment" (editable)
  - Add field: "Number of students who passed the assessment" (editable)
  - Calculate percentage: `(students_passed / students_took) * 100`
- **Validation Rules:**
  - `students_took` cannot exceed `enrollment`
  - `students_passed` cannot exceed `students_took`
- **Priority:** CRITICAL - Blocks Spring 2026 launch
- **Affects:**
  - Database schema (CourseOutcome model)
  - Instructor data entry UI (assessments.html)
  - Export format
  - Reporting/calculation logic

---

### 2. Assessment Tool Identification vs. Narrative

**Quote (10:54-11:41):**

> "You have a narrative, but I don't know that we want them. I don't think, I think that's too much data to have a narrative for each individual clue that's being assessed. Okay, what we do need is that text box where they identify what their assessment tool is. So it simply says, you know, test number 315, people took it, 13 people passed. Here's the percentage. Okay, I think you can convert that text box probably to what their assessment tool was."

**Quote (11:41-11:52):**

> "yeah, I give them like 40 characters. We don't get much, like 4050, characters, whatever fits in there nicely. It's just enough for them to remember what assignment that they used."

**Follow-up Item 2.1: Replace Per-CLO Narrative with Assessment Tool Field**

- **⚠️ IMPLEMENTATION ERROR:** We incorrectly placed narrative fields at the CLO level when they should only exist at the course level. This is not a new requirement - it's correcting a misunderstanding of the original specification.
- **Current State:** Each CLO has a narrative/notes field (unlimited length) - **THIS IS WRONG**
- **Required State:**
  - **Remove** narrative field from individual CLO assessment entry
  - Add "Assessment Tool" text field (40-50 character limit)
  - Purpose: Quick reference (e.g., "Test #3", "Final Project", "Lab Practical 2")
- **Priority:** HIGH - Expected for Spring 2026
- **Migration Impact:** Any existing CLO-level narrative data needs to be migrated or discarded
- **Affects:**
  - Database schema (CourseOutcome model)
  - Instructor data entry UI (assessments.html)
  - Export format
  - User stories (Instructor Story #8)
  - Any existing test data with CLO narratives

---

### 3. Course-Level Narrative and Enrollment Data

**Quote (11:57-12:23):**

> "I've been to other colleges where you have these lengthy descriptions of the assignment. It's like, Nah, we don't need that. But then for an overall course, there is a narrative, celebrations, challenges and changes. You probably saw that on the documentation."

**Quote (12:23-12:46):**

> "yeah, the course is a whole as is the enrollment, the number of students withdrew, and then the faculty member would populate how many passed and how many DFI seed, okay, a D, an F or an incomplete and that helps us compute our pass rate."

**Follow-up Item 3.1: Add Course-Level Data Section**

- **⚠️ IMPLEMENTATION ERROR:** Narratives belong at the course level, NOT the CLO level (see Item 2.1). This section is where narratives should have been all along.
- **Current State:** No course-level summary section (only CLO-level data)
- **Required State:**
  - Add course-level section to instructor data entry
  - **Pre-populated (read-only):**
    - Total enrollment
    - Number of withdrawals
  - **Instructor-entered:**
    - Number of students who passed (A, B, C grades)
    - Number of students with DFIC (D, F, Incomplete)
  - **Narrative (3 sections):**
    - Celebrations (free text)
    - Challenges (free text)
    - Changes (free text planned for next offering)
- **Calculation:** Pass rate = `passed / (enrollment - withdrawals)` × 100
- **Priority:** CRITICAL - Blocks Spring 2026 launch
- **Affects:**
  - Database schema (new Course model fields or related table)
  - Instructor data entry UI (new section in assessments.html)
  - Export format
  - Instructor user stories

---

### 3.2. Enrollment Reconciliation Issues - "Cannot Reconcile" Checkbox

**Quote (9:41-10:54):** _(Implicit in the "students don't show up" discussion)_

> "So it pre populated how many students were in the course, and so every student that's in the course does not necessarily take the assessment. Okay? Students literally don't show up for class, right?"

**Related User Story (INSTRUCTOR_USER_STORIES.md, Story #9a):**

> **9a. Handle Enrollment Reconciliation Issues**  
> **As an instructor, I want to** check a "cannot reconcile" box when the formula (enrollment - withdrawals - pass - DFIC) does not equal zero **so that** I can proceed with submission when the numbers don't match due to data timing or other institutional factors.

**Follow-up Item 3.2: Add "Cannot Reconcile" Checkbox**

- **Context:** Enrollment numbers sometimes don't balance due to:
  - Timing mismatches between systems
  - Late adds/drops not reflected in feed
  - Administrative corrections
  - Data entry errors in source system
- **Current State:** No mechanism to handle reconciliation failures
- **Required State:**
  - Add "Cannot Reconcile" checkbox to course-level enrollment section
  - When checked:
    - Bypass validation that enrollment - withdrawals = passed + DFIC
    - Optional: Add text field for brief explanation (e.g., "Late drop not in system")
    - Flag submission for admin review (visual indicator in audit view)
  - When unchecked (default):
    - Enforce validation: enrollment - withdrawals MUST equal passed + DFIC
    - Show error message if numbers don't balance
- **Distinct from NCI:** This is about DATA INTEGRITY issues, not missing instructors
- **Priority:** HIGH - Important for instructor workflow, but workaround exists (manual follow-up)
- **Affects:**
  - Database schema (Course model or related table)
  - Instructor data entry UI (assessments.html)
  - Validation logic (client-side and server-side)
  - Audit view (flag for admin review)

---

### 4. "Never Coming In" (NCI) Status for CLO Audit

**Quote (14:47-15:35):**

> "And then when we got all of them to either be okay, this might have come up. After the last time we talked, they're all going to either be approved. I mean, like, at some point they're all going to be approved, or we have to be able to mark them, as I call it, MCI, never coming in. Okay, right? You're really going to get 100% participation. I try really hard, but people move. People quit answering their email. They resigned from the institution the I see, whatever right so"

**Quote (15:35-15:59):**

> "it is, and so that way is I sent out. 198 of them are approved at this point. Two of them are never coming in, because I don't want it to keep on coming up as as still out, still out, still out, right, still out. And then there's I already know they're never coming in, so that would be another piece."

**Quote (16:10-16:32):**

> "yeah, so at some point I need to know that everybody's done their thing right and and who hasn't done their thing, and it looks like this is the screen that it's approved, never coming in, or it needs reworked, and then at some point I'm going to resolve all the needs we worked and they're going to move into the approval column."

**Follow-up Item 4.1: Add "Never Coming In" (NCI) Status**

- **Current State:** Audit workflow has two outcomes: "Approved" or "Needs Rework"
- **Required State:**
  - Add third outcome: "Never Coming In" (NCI)
  - **Use Cases:**
    - Instructor left institution
    - Instructor non-responsive despite multiple reminders
    - Course cancelled/dropped after initial assignment
  - **UI Changes:**
    - Add "Mark as NCI" button to audit interface
    - Optional: Add reason/note field for NCI designation
    - Filter/group NCI submissions separately from pending
  - **Dashboard Impact:**
    - NCI items should not show as "still out" in pending counts
    - Track separately for completion reporting (e.g., "198 approved, 2 NCI, 15 pending")
- **Priority:** HIGH - Critical for Leslie's workflow management
- **Affects:**
  - Database schema (audit status enum)
  - Audit UI (audit_clo.html, dashboard displays)
  - Reporting/completion tracking
  - Program admin user stories

---

## Export and Data Flow Requirements

### 5. Bi-directional Export Format Validation

**Quote (18:26-19:27):**

> "I do have a question for you, and it's something that I'm not entirely clear on so let's say we've got all the bugs smoothed out. This entire system works great. You get all of the information filled out that you need. Now the way I've set up the import is that everything is bi directional, so whatever the format is of the import that I'm using to get all the data in, I can export it in exactly the same way, so we can add data and then we can export it, but I'm not sure, from your perspective, how you want to take it into your existing system after we've done all this to collect everything. So it's possible that I could just do an export and then you could import it into access. That's probably likely the way it would work. Yeah. Okay, I would have a concern that I might mess up your database if I didn't do a lot of due diligence to make sure that that import was going to go well."

**Quote (19:52-22:11):**

> "Like I said, I have, I have my bubble my bubble gum database, right is buggy right now, which we knew it would be a second last. Forever, because I'm not a programmer, and I don't know where they are on the it, the one that it is building right now. They don't know that we're collaborating, and I'm not quite ready to let them know that we're collaborating, because they're working on their stuff as well, to try and see what we can do. Um, but I could at least be able to show you what we do with the data. I mean, I don't know what your table looks like, I guess. I guess what you have is what you have, what I sent you, and then it would be populated. Correct. So in reality, will right now, what I'm doing is I would have all of that data, and then I end up pulling it into like 28 programs or whatever, pulling the 28 spreadsheets and then and then to be able to get 10 sections of English, 101, I want to know overall, for flow one, or for clue one, how many students took it, how many students passed it, to know if That course is satisfactory, right? So it's sort of a group, a subtotal kind of thing. It's really basically in that same format, and then they have to go through and manually attach it back to program outcomes, which is outside the scope of what we're working on. Okay? So really, it just, it really comes back to that same spreadsheet, sorted by course, so no longer by instructor or whatever, sorted by course, sorted by clo and then, and then as a subtotal for each clo, so that It captures all of the various sections of that class."

**Follow-up Item 5.1: Validate Export Format with Leslie**

- **DEFERRED:** Not needed for initial implementation phase
- **Rationale:** Export adapter already exists and uses same format as import (CEI Excel v1.2). Validation can occur during UAT.
- **Future Action:** Validate with Leslie during UAT phase
- **Priority:** DEFERRED - Will address during UAT

---

### 6. Program Aggregation and Reporting (Out of Scope - Documented)

**Quote (19:52-22:11):** _(same quote as above)_

> "...and then they have to go through and manually attach it back to program outcomes, which is outside the scope of what we're working on."

**Follow-up Item 6.1: Document Out-of-Scope Functionality**

- **NOT NEEDED:** No action required
- **Scope Decision:** This aggregation/reporting is OUT OF SCOPE permanently
- **What Leslie Does Manually (for reference only):**
  1. Pulls data into 28 separate program spreadsheets
  2. Aggregates CLO results across all sections
  3. Calculates subtotals
  4. Maps course CLOs to program outcomes
- **Rationale:** Leslie has existing workflow; focus on core "push out and pull back" only
- **Priority:** N/A - No action needed

---

## Workflow and Timeline

### 7. Course-Specific Deadlines for Rolling Submissions

**Quote (16:43-18:22):**

> "last semester was all done. It's just I had to do it manually. So it took a little longer than it and it should have my 28 spreadsheets. So everything in the fall we assess all courses. So in this this semester, there's 460 individual sections. So, you know, we assess all of those. They're all due on a certain day. The day after grades are due, they're all due. Okay, they might trickle in for the rest of that week, but that should be pretty much it, except for early college classes and I'm coming later, which is why I tried to sort of set it up. As you know, we've This batch is ready, and the other batches are going to come in until later, because the high school classes, when we're teaching college classes at the high school, their last day of instruction might be well into January, whereas the rest of the campus is done. Our campus is done, first week, second week of December. Yeah. So there, you know. So, so at some point, you know, like I said, so it's done, I can import this many into the system, but then there's always going to be some that are still coming along, and then it never came, never coming in."

**Follow-up Item 7.1: Add Due Date Field to Course Offerings**

- **Operational Context:**
  - Main campus courses: deadline day after grades (early/mid-December)
  - Early college courses: may extend into January
  - Leslie needs flexibility to set different deadlines per course
- **Solution:**
  - Add **"Due Date"** field to Course/Section model
  - Use calendar date picker (simple date selector)
  - No dropdown of cohorts needed - just set specific date per course
  - Can be populated during import or set manually
  - Dashboard can filter/sort by due date
  - Reminder emails reference the specific course due date
- **Benefits:**
  - Maximum flexibility - each course can have unique deadline
  - Simple implementation - just one date field
  - Supports any future edge cases automatically
- **Priority:** HIGH - Needed for operational workflow
- **Affects:**
  - Database schema (Course/Section model - add `due_date` field)
  - Import adapter (parse due date from feed if present)
  - Instructor dashboard (show due date)
  - Reminder email templates (use course-specific date)
  - Admin dashboard (filter/sort by due date)

---

### 8. Spring 2026 Launch Target

**Quote (22:47-23:11):**

> "well, if we were going to utilize it this semester, which I think is probably pretty unlikely, we're three weeks out. Okay, so I think that's probably unlikely. So then the next assessment period would be spring semester, so that's mid, mid April. We would have to be ready to rock and roll."

**Quote (23:11-24:02):**

> "Okay. Well, how would this sound for a timeline? Then I've got lots of little wrinkles I still need to iron out and, you know, functionality and stuff, but I feel very comfortable about having something ready by April, so maybe I could get to the point where the website is kind of fully functional, and then hand it over to you, to you and Matt to kind of beat it up and tell me what's not working or what we don't need and that kind of thing, and we can kind of finalize how everything looks and works in the end of fall and winter, and then in the end of winter and beginning of spring, we could actually start ramping up to actually use it in the spring semester and get users, get accounts created for instructors and that kind of stuff."

**Follow-up Item 8.1: Project Timeline (Reference Only)**

- **NO ACTION NEEDED RIGHT NOW:** Timeline is agreed upon, proceed with implementation
- **Target Go-Live:** Spring 2026 semester (mid-April 2026 deadline)
- **Development Timeline:**
  - Fall/Winter 2025-2026: Build out full functionality
  - End of Winter 2026: Hand off to Leslie and Matt for UAT
  - Late Winter/Early Spring 2026: Refinement based on feedback
  - Early Spring 2026: Production setup, instructor account creation
  - Mid-April 2026: First live assessment cycle
- **Priority:** N/A - Reference only

---

## Minor Issues and Enhancements

### 9. Reminder Email Direct Link Bug

**Quote (7:59-8:21):**

> "there's a little bug in that point where it doesn't actually take you directly to take you directly to the page, but ideally we take you back here, and then you'd go through for each of your Clos and enter."

**Follow-up Item 9.1: Fix Reminder Email Deep Link**

- **Issue:** Clicking reminder email link doesn't take instructor directly to assessment page
- **Expected Behavior:** Instructor clicks link → auto-login (if cookie exists) → land on assessment page
- **Priority:** LOW - Convenience feature, workaround exists (manual navigation)
- **Affects:** Email service (reminder template), URL generation

---

## Strategic Considerations

### 10. CEI IT Department and Parallel Development

**Quote (19:52-22:11):**

> "I don't know where they are on the it, the one that it is building right now. They don't know that we're collaborating, and I'm not quite ready to let them know that we're collaborating, because they're working on their stuff as well, to try and see what we can do."

**Follow-up Item 10.1: Monitor CEI IT Development**

- **NO ACTION NEEDED RIGHT NOW:** Awareness only, no implementation tasks
- **Context:** CEI IT is building their own system in parallel
- **Leslie's Strategy:** Keep Lassie project "under the radar" until proven
- **Risk:** Potential overlap, duplication, or institutional politics
- **Mitigation:** Focus on delivering value quickly, be prepared to adapt or integrate
- **Priority:** N/A - Strategic awareness only

---

## Summary of Action Items by Priority

### CRITICAL (Blocks Spring 2026 Launch)

1. **Modify CLO assessment data model** - Students took vs. passed (Item 1.1)
2. **Add course-level enrollment and narrative section** - Narratives belong here, NOT at CLO level (Item 3.1)

### HIGH (Expected for Spring 2026)

3. **Replace per-CLO narrative with assessment tool field** - Fix implementation error (Item 2.1)
4. **Add "Cannot Reconcile" checkbox for enrollment mismatches** (Item 3.2)
5. **Add "Never Coming In" (NCI) status to audit workflow** (Item 4.1)
6. **Add due date field to course offerings** - Calendar selector for flexible deadlines (Item 7.1)

### LOW (Nice to have)

7. **Fix reminder email deep link** (Item 9.1)

### DEFERRED/NOT NEEDED (No immediate action)

- ~~Validate export format with Leslie~~ (Item 5.1) - Defer to UAT
- ~~Document out-of-scope aggregation~~ (Item 6.1) - No action needed
- ~~Confirm project timeline~~ (Item 8.1) - Reference only
- ~~Monitor CEI IT development~~ (Item 10.1) - Awareness only

---

## Next Steps - Implementation Phase

### Immediate Focus (CRITICAL Items)

1. **Database Schema Design:** Design migrations for:
   - CLO assessment data model (students_took, students_passed)
   - Course-level enrollment section (withdrawals, passed, DFIC, cannot_reconcile flag)
   - Course-level narrative section (celebrations, challenges, changes)
   - Remove CLO-level narrative fields (breaking change)
   - Add assessment_tool field to CLO assessments (40-50 char limit)

2. **User Story Updates:** Revise instructor user stories to reflect:
   - Corrected CLO assessment workflow (took vs. passed)
   - Course-level narrative placement (not CLO-level)
   - Assessment tool field instead of CLO narrative
   - Cannot reconcile checkbox

### Secondary Focus (HIGH Items)

3. **Audit Workflow Enhancement:**
   - Add "Never Coming In" (NCI) status option
   - Update audit UI and status enum
   - Dashboard filtering and tracking for NCI items

4. **Deadline Management:**
   - Add due_date field to Course/Section model
   - Calendar picker in UI (import + manual entry)
   - Update reminder emails to use course-specific dates
   - Dashboard filtering by due date

### Lower Priority

5. **Email Deep Link Fix:** Reminder email direct navigation (Item 9.1)

### Ready for Implementation Planning

All critical requirements are now clarified and scoped. Ready to proceed with detailed technical design and implementation.

---

## Positive Feedback Received

**Quote (9:41):**

> "Basically, yeah. I mean, it looks pretty close"

**Quote (13:30-13:45):**

> "Yep, that's exactly. That's exactly... Okay, okay, yeah, I like it. Okay, well, good."

**Quote (24:02-24:11):**

> "sounds great to me. Matt, yeah, that sounds pretty reasonable."

**Overall Sentiment:** Demo validated core workflow concept. Refinements needed but direction approved.
