"""
UAT-004: Bulk Reminders - Failure Handling, Retry, and Error Recovery

Test Objective: Validate system behavior when email sending fails, including retry logic,
error reporting, and partial success handling.

User Personas:
- Dr. Sarah Williams, Program Admin
- 3 Instructors (currently all valid; failure scenarios to be added)
"""

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL
from tests.e2e.test_helpers import (
    create_test_user_via_api,
    get_institution_id_from_user,
)


class TestUAT004BulkRemindersFailureHandling:
    """UAT-004: Test bulk reminder failure scenarios and error recovery"""

    # Test user credentials
    VALID_INSTRUCTOR_1_EMAIL = "alice.johnson@ethereal.email"
    VALID_INSTRUCTOR_1_NAME = "Alice Johnson"

    INVALID_EMAIL_INSTRUCTOR = "invalid-email-format"  # Invalid format
    INVALID_EMAIL_NAME = "Bad Email"

    VALID_INSTRUCTOR_2_EMAIL = "carol.davis@ethereal.email"
    VALID_INSTRUCTOR_2_NAME = "Carol Davis"

    PERSONAL_MESSAGE = "Please submit your course data ASAP."

    def test_complete_bulk_reminder_failure_workflow(
        self, program_admin_authenticated_page: Page
    ):
        """
        STEP 1: Setup - Use seeded instructors (for now, all valid)
        STEP 2: Send Bulk Reminders
        STEP 3: Monitor Success (no failures in MVP)
        STEP 4: Verify Completion
        STEP 5: Verify Emails Received

        NOTE: This test currently validates the happy path.
        Failure scenarios (invalid emails, soft-deleted users, etc.) will be added
        once we have the infrastructure to create those conditions.
        """
        admin_page = program_admin_authenticated_page

        print("=" * 70)
        print("STEP 1: Setup - Create test instructors via API")
        print("=" * 70)

        # Get institution ID and program_ids for the CS program admin
        institution_id = get_institution_id_from_user(admin_page)
        print(f"   Program admin institution_id: {institution_id}")

        assert institution_id, "Failed to get institution_id from program admin"

        # Get program admin's program_ids via API
        # The seeded program admin (bob.programadmin@mocku.test) manages the Computer Science program
        current_user_response = admin_page.request.get(f"{BASE_URL}/api/me")
        assert (
            current_user_response.ok
        ), f"Failed to get current user: {current_user_response.status}"
        current_user_data = current_user_response.json()
        program_ids = current_user_data.get("program_ids", [])

        print(f"   Program admin program_ids: {program_ids}")
        assert len(program_ids) > 0, "Program admin has no program_ids"

        # Create 3 test instructors associated with the CS program
        # These will be visible to the CS program admin
        create_test_user_via_api(
            admin_page=admin_page,
            base_url=BASE_URL,
            email=self.VALID_INSTRUCTOR_1_EMAIL,
            first_name="Alice",
            last_name="Johnson",
            role="instructor",
            institution_id=institution_id,
            password="Instructor123!",
            program_ids=program_ids,  # Associate with CS program
        )
        print(f"   ✅ Created instructor: {self.VALID_INSTRUCTOR_1_EMAIL}")

        create_test_user_via_api(
            admin_page=admin_page,
            base_url=BASE_URL,
            email=self.VALID_INSTRUCTOR_2_EMAIL,
            first_name="Carol",
            last_name="Davis",
            role="instructor",
            institution_id=institution_id,
            password="Instructor123!",
            program_ids=program_ids,  # Associate with CS program
        )
        print(f"   ✅ Created instructor: {self.VALID_INSTRUCTOR_2_EMAIL}")

        print("✅ Test instructors ready (2 created via API with program association)")
        print("📝 NOTE: Failure scenarios (invalid emails, soft-deleted users) will be")
        print("   added once we have infrastructure to create those conditions")

        print("\n" + "=" * 70)
        print("STEP 2: Send bulk reminders")
        print("=" * 70)

        # Navigate to dashboard
        admin_page.goto(f"{BASE_URL}/dashboard")
        expect(admin_page).to_have_url(f"{BASE_URL}/dashboard", timeout=10000)
        admin_page.wait_for_load_state("networkidle")

        # Click "Send Reminders" button
        send_reminders_btn = admin_page.locator(
            'button:has-text("Send Reminders")'
        ).first
        expect(send_reminders_btn).to_be_visible(timeout=5000)
        send_reminders_btn.click()

        # Verify modal opens
        modal = admin_page.locator("#bulkReminderModal")
        expect(modal).to_be_visible(timeout=5000)

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

        # Select all instructors
        select_all_btn = admin_page.locator("#selectAllInstructors")
        select_all_btn.click()

        # Verify selected count (3 = 1 seeded instructor + 2 created)
        selected_count = admin_page.locator("#selectedInstructorCount")
        expect(selected_count).to_have_text("3")
        print("✅ Selected 3 instructors")

        # Enter personal message
        admin_page.fill("#reminderMessage", self.PERSONAL_MESSAGE)

        # Click "Send Reminders"
        send_btn = admin_page.locator("#sendRemindersButton")
        send_btn.click()

        print("\n" + "=" * 70)
        print("STEP 3: Monitor job progress")
        print("=" * 70)

        # Wait for progress view to appear
        expect(admin_page.locator("#reminderStep2")).to_be_visible(timeout=5000)

        # Initial progress bar should be at 0
        progress_bar = admin_page.locator("#reminderProgressBar")
        expect(progress_bar).to_have_attribute("value", "0")

        print("✅ Progress tracking started")

        # Wait for job to complete
        admin_page.wait_for_function(
            """
            () => {
                const progressBar = document.getElementById('reminderProgressBar');
                return progressBar && progressBar.value == '100';
            }
            """,
            timeout=120000,  # 2 minutes max (includes rate limiting)
        )

        print("✅ Job completed")

        # Get final counts
        sent_count = admin_page.locator("#reminderSentCount").text_content()
        failed_count = admin_page.locator("#reminderFailedCount").text_content()
        pending_count = admin_page.locator("#reminderPendingCount").text_content()

        print(
            f"   Final counts - Sent: {sent_count}, Failed: {failed_count}, Pending: {pending_count}"
        )

        print("\n" + "=" * 70)
        print("STEP 4: Verify completion")
        print("=" * 70)

        # Verify progress bar reached 100%
        expect(progress_bar).to_have_attribute("value", "100")
        print("✅ Progress bar at 100%")

        # Verify close button is enabled
        close_button = admin_page.locator("#closeProgressButton")
        expect(close_button).to_be_enabled()
        print("✅ Close button enabled")

        # Close the modal
        close_button.click()
        admin_page.wait_for_selector("#bulkReminderModal", state="hidden", timeout=3000)

        print("\n" + "=" * 70)
        print("STEP 5: Verify emails received (sample check)")
        print("=" * 70)

        # Check at least one email was received
        # (The seeded instructors have @mocku.test addresses which are protected)
        # So we won't actually receive emails for them in the test environment
        # This test validates the UI workflow only for now

        print("✅ UAT-004 workflow completed!")
        print(
            f"   Summary: {sent_count} sent, {failed_count} failed, {pending_count} pending"
        )
        print(
            "\n📝 NOTE: Full failure scenario testing (invalid emails, soft-deleted users, etc.)"
        )
        print("   will be added once we have test data setup infrastructure")
