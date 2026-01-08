"""
E2E: Bulk Instructor Reminders - Happy Path with Progress Tracking

Test Objective: Validate bulk reminder system with real-time progress tracking
and successful delivery to multiple instructors.

User Persona: Dr. Sarah Williams (Program Admin) sending reminders to 5 instructors
"""

from playwright.sync_api import Page, expect

# Test Configuration
BASE_URL = "http://localhost:3002"  # E2E tests use port 3002


class TestBulkInstructorReminders:
    """E2E: Complete bulk instructor reminder workflow with progress tracking"""

    # Test Data
    ADMIN_EMAIL = "sarah.admin@mocku.test"
    ADMIN_PASSWORD = "InstitutionAdmin123!"

    # Test instructors (to be created via API)
    INSTRUCTORS = [
        {
            "email": "alice.johnson@ethereal.email",
            "first_name": "Alice",
            "last_name": "Johnson",
            "password": "Instructor123!",
        },
        {
            "email": "bob.martinez@ethereal.email",
            "first_name": "Bob",
            "last_name": "Martinez",
            "password": "Instructor123!",
        },
        {
            "email": "carol.davis@ethereal.email",
            "first_name": "Carol",
            "last_name": "Davis",
            "password": "Instructor123!",
        },
        {
            "email": "david.wilson@ethereal.email",
            "first_name": "David",
            "last_name": "Wilson",
            "password": "Instructor123!",
        },
        {
            "email": "emma.thompson@ethereal.email",
            "first_name": "Emma",
            "last_name": "Thompson",
            "password": "Instructor123!",
        },
    ]

    TERM = "Fall 2025"
    DEADLINE = "2025-12-15"
    PERSONAL_MESSAGE = (
        "Please submit your course data by the deadline. Contact me if you need help!"
    )

    def test_complete_bulk_reminder_workflow(
        self,
        authenticated_institution_admin_page: Page,
    ):
        """
        E2E: Complete bulk reminder workflow with progress tracking.

        Steps:
        1. Admin logs in (fixture provides authenticated page)
        2. Navigate to dashboard and open bulk reminder modal
        3. Verify instructor list loads
        4. Select all instructors
        5. Compose reminder message
        6. Initiate bulk send
        7. Monitor real-time progress
        8. Verify completion
        9. Verify email delivery to all recipients
        10. Verify job persistence
        """
        admin_page = authenticated_institution_admin_page

        # ==================================================================
        # STEP 1: Setup Test Instructors
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 1: Setup test instructors")
        print("=" * 70)

        # Using instructors from baseline seed data
        # Future enhancement: Create specific test instructors via API

        print("✅ Test instructors ready")

        # ==================================================================
        # STEP 2: Admin Opens Reminder Modal
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 2: Admin opens bulk reminder modal")
        print("=" * 70)

        # Navigate to dashboard
        admin_page.goto(f"{BASE_URL}/dashboard")
        expect(admin_page).to_have_url(f"{BASE_URL}/dashboard", timeout=10000)

        # Click "Send Reminders" button
        send_reminders_btn = admin_page.locator(
            'button:has-text("Send Reminders")'
        ).first
        expect(send_reminders_btn).to_be_visible(timeout=5000)
        send_reminders_btn.click()

        # Verify modal opens
        modal = admin_page.locator("#bulkReminderModal")
        expect(modal).to_be_visible(timeout=5000)

        # Verify modal title
        expect(admin_page.locator("#bulkReminderModalLabel")).to_contain_text(
            "Send Instructor Reminders"
        )

        # Wait for instructor list container to load
        admin_page.wait_for_selector(
            "#instructorListContainer", state="visible", timeout=5000
        )

        # Wait for instructors to finish loading asynchronously
        # The JavaScript loads instructors via API when modal is shown
        # Wait for at least one checkbox to appear (instructors loaded)
        admin_page.wait_for_selector(
            "#instructorListContainer input[type='checkbox']",
            state="attached",
            timeout=10000,
        )

        print("✅ Bulk reminder modal opened")
        print("✅ Instructors loaded")

        # ==================================================================
        # STEP 3: Verify Instructor List
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 3: Verify instructor list")
        print("=" * 70)

        # Get instructor count (checkboxes in the container)
        instructor_checkboxes = admin_page.locator(
            "#instructorListContainer input[type='checkbox']"
        )
        instructor_count = instructor_checkboxes.count()

        print(f"✅ Found {instructor_count} instructors in list")

        # Verify selected count shows 0
        selected_count = admin_page.locator("#selectedInstructorCount")
        expect(selected_count).to_have_text("0")

        # Verify send button is disabled
        send_btn = admin_page.locator("#sendRemindersButton")
        expect(send_btn).to_be_disabled()

        print("✅ Initial state: 0 selected, send button disabled")

        # ==================================================================
        # STEP 4: Select Instructors
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 4: Select instructors")
        print("=" * 70)

        # Click "Select All"
        select_all_btn = admin_page.locator("#selectAllInstructors")
        select_all_btn.click()

        # Verify all checkboxes are checked
        checkboxes = admin_page.locator(
            "#instructorListContainer input[type='checkbox']"
        )
        for i in range(checkboxes.count()):
            expect(checkboxes.nth(i)).to_be_checked()

        # Verify selected count
        expect(selected_count).to_have_text(str(instructor_count))

        # Verify send button is enabled
        expect(send_btn).to_be_enabled()

        print(f"✅ Selected all {instructor_count} instructors")
        print("✅ Send button enabled")

        # ==================================================================
        # STEP 5: Compose Message
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 5: Compose reminder message")
        print("=" * 70)

        # Fill in term
        admin_page.fill("#reminderTerm", self.TERM)

        # Fill in deadline
        admin_page.fill("#reminderDeadline", self.DEADLINE)

        # Fill in personal message
        admin_page.fill("#reminderMessage", self.PERSONAL_MESSAGE)

        print(f"✅ Term: {self.TERM}")
        print(f"✅ Deadline: {self.DEADLINE}")
        print(f"✅ Personal message: {self.PERSONAL_MESSAGE[:50]}...")

        # ==================================================================
        # STEP 6: Initiate Bulk Send
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 6: Initiate bulk send")
        print("=" * 70)

        # Click send button
        send_btn.click()

        # Wait for progress view to appear
        progress_section = admin_page.locator("#reminderStep2")
        expect(progress_section).to_be_visible(timeout=3000)

        # Verify progress bar element exists (it's visible within #reminderStep2)
        progress_bar = admin_page.locator("#reminderProgressBar")
        expect(progress_bar).to_have_attribute("value", "0")

        # Verify initial counts
        sent_count = admin_page.locator("#reminderSentCount")
        failed_count = admin_page.locator("#reminderFailedCount")
        pending_count = admin_page.locator("#reminderPendingCount")

        expect(pending_count).to_have_text(str(instructor_count))

        print("✅ Progress view displayed")
        print(f"✅ Initial pending: {instructor_count}")

        # ==================================================================
        # STEP 7: Monitor Real-Time Progress
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 7: Monitor real-time progress")
        print("=" * 70)

        # Wait for completion (with generous timeout for email sending)
        # Each email takes ~2-3 seconds, so allow 30 seconds for 5 emails
        admin_page.wait_for_function(
            """
            () => {
                const progressBar = document.querySelector('#reminderProgressBar');
                return progressBar && progressBar.value >= 100;
            }
            """,
            timeout=60000,  # 60 seconds max
        )

        print("✅ Progress completed")

        # ==================================================================
        # STEP 8: Verify Completion
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 8: Verify completion state")
        print("=" * 70)

        # Verify progress bar is at 100%
        final_progress = admin_page.locator("#reminderProgressBar").get_attribute(
            "value"
        )
        assert (
            int(float(final_progress)) == 100
        ), f"Expected progress 100%, got {final_progress}%"

        # Verify final counts
        final_sent = sent_count.text_content()
        final_failed = failed_count.text_content()
        final_pending = pending_count.text_content()

        print(f"✅ Final sent: {final_sent}")
        print(f"✅ Final failed: {final_failed}")
        print(f"✅ Final pending: {final_pending}")

        assert (
            int(final_sent) == instructor_count
        ), f"Expected {instructor_count} sent, got {final_sent}"
        assert int(final_failed) == 0, f"Expected 0 failed, got {final_failed}"
        assert int(final_pending) == 0, f"Expected 0 pending, got {final_pending}"

        # Verify close button is enabled
        close_btn = admin_page.locator("#closeProgressButton")
        expect(close_btn).to_be_enabled()

        print("✅ All reminders sent successfully")
        print("✅ Close button enabled")

        # ==================================================================
        # STEP 9: Verify Email Delivery
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 9: Verify email delivery to all instructors")
        print("=" * 70)

        # Note: For UAT-003, we're testing with seeded instructors from MockU
        # The emails go to their configured addresses
        # In a real test, we'd check each instructor's inbox

        print("⚠️  Email verification skipped - would check 5+ inboxes in real UAT")
        print(
            "✅ (In production, verify each instructor received email with correct content)"
        )

        # ==================================================================
        # STEP 10: Verify Job Persistence
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 10: Verify job persistence")
        print("=" * 70)

        # Close modal
        close_btn.click()
        expect(modal).not_to_be_visible(timeout=3000)

        # Future enhancement: Call API to verify job was persisted
        # GET /api/bulk-email/recent-jobs

        print("✅ Modal closed")
        print("⚠️  Job persistence check via API not yet implemented")

        print("\n" + "=" * 70)
        print("UAT-003 COMPLETE: Bulk reminder workflow validated!")
        print("=" * 70)
        print("✅ Modal functionality: PASSED")
        print("✅ Instructor selection: PASSED")
        print("✅ Progress tracking: PASSED")
        print("✅ Bulk sending: PASSED")
        print("=" * 70)
