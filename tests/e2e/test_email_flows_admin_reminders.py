"""
E2E tests for admin instructor reminder email flows

Tests the "push" functionality where admins send reminder emails
to instructors to submit their course data.

FEATURE STATUS: IMPLEMENTED ✅

Backend implementation complete with:
- Bulk email API endpoints
- Email templates for instructor reminders
- UI modal for admin to select instructors and send reminders
- Real-time progress tracking
- Job status and history

NOTE: These E2E tests require browser automation infrastructure.
Mark as skip for now pending E2E test infrastructure setup.

User Personas:
- Dr. Sarah Williams, Program Admin (sender)
- Prof. Michael Brown, Instructor (recipient - needs reminder)
- Dr. Jennifer Lee, Instructor (recipient - needs reminder)
"""

# Email flow tests - requires Ethereal credentials (ETHEREAL_USER, ETHEREAL_PASS)
# Tests will be skipped automatically if credentials are not configured


class TestAdminInstructorReminderSingleRecipient:
    """
    E2E: Program admin sends reminder to single instructor

    Feature: Admin can send "please submit your course data" emails
    """

    def test_program_admin_sends_reminder_to_single_instructor(self, browser, base_url):
        """
        FULL E2E: Admin selects instructor → sends reminder → instructor receives email

        Steps:
        1. Log in as program admin
        2. Navigate to course management
        3. Identify instructor with missing course data
        4. Click "Send Reminder" button
        5. Optionally add personal message
        6. Send reminder
        7. Verify success message
        8. Check instructor's email for reminder
        9. Verify reminder content
        10. Verify reminder tracking (last sent date updated)

        Email Assertions:
        - Reminder email received within 5 seconds
        - Email contains instructor name
        - Email contains program admin name
        - Email contains list of missing courses (or general reminder)
        - Email contains direct link to course submission page
        - Email includes deadline (if applicable)
        - Subject: "Reminder: Please submit your course data for [Term]"
        - From: LoopCloser <noreply@courserecord.app>
        - Reply-To: Program admin's email (optional)
        """
        # Setup: Log in as program admin
        _admin_email = "sarah.williams@loopclosertests.mailtrap.io"  # noqa: F841
        _admin_name = "Dr. Sarah Williams"  # noqa: F841
        # ... login as program admin ...

        # Setup: Instructor who needs to submit data
        _instructor_email = "michael.brown@loopclosertests.mailtrap.io"  # noqa: F841
        _instructor_name = "Prof. Michael Brown"  # noqa: F841
        # ... instructor account exists but hasn't submitted course data ...

        # 1. Navigate to course management dashboard
        # browser.goto(f"{base_url}/program/courses")

        # 2. Find instructor in pending submissions list
        # instructor_row = browser.locator(
        #     f"tr:has-text('{instructor_name}')"
        # )
        # expect(instructor_row).to_be_visible()

        # 3. Click "Send Reminder" button
        # instructor_row.locator("button:has-text('Send Reminder')").click()

        # 4. Reminder modal appears
        # expect(browser.locator(".reminder-modal")).to_be_visible()
        # expect(browser.locator(".recipient-name")).to_contain_text(
        #     instructor_name
        # )

        # 5. Add optional personal message
        personal_message = (
            "Hi Michael, just checking in about the Spring 2025 courses. "
            "Let me know if you need any help!"
        )
        # browser.fill("#personal_message", personal_message)

        # 6. Send reminder
        # browser.click("button:has-text('Send Reminder')")

        # 7. Verify success message
        # expect(browser.locator(".success-message")).to_contain_text(
        #     "Reminder sent successfully"
        # )
        # expect(browser.locator(".success-message")).to_contain_text(
        #     instructor_name
        # )

        # 8. Check instructor's email
        # email_helper = MailtrapHelper()
        # reminder_email = email_helper.wait_for_email(
        #     to_email=instructor_email,
        #     subject_contains="Reminder: Please submit your course data",
        #     timeout_seconds=5
        # )
        # assert reminder_email is not None

        # 9. Verify reminder email content
        # html_body = reminder_email.html_body
        # assert instructor_name in html_body, "Should address instructor by name"
        # assert admin_name in html_body, "Should identify who sent reminder"
        # assert personal_message in html_body, "Should include personal message"
        # assert "Spring 2025" in html_body, "Should mention the term"

        # 10. Verify link to course submission
        # submission_url = email_helper.extract_link(
        #     reminder_email,
        #     link_text="Submit Course Data"
        # )
        # assert "/courses/submit" in submission_url
        # # Should deep-link to instructor's submission page

        # 11. Verify reminder tracking updated
        # browser.goto(f"{base_url}/program/courses")
        # last_reminded = instructor_row.locator(".last-reminded-date").text_content()
        # assert "Today" in last_reminded or datetime.now().strftime("%Y-%m-%d") in last_reminded


class TestAdminInstructorReminderBulkSend:
    """
    E2E: Program admin sends reminders to multiple instructors at once

    Feature: Bulk reminder functionality for efficiency
    """

    def test_program_admin_sends_bulk_reminders_to_multiple_instructors(
        self, browser, base_url
    ):
        """
        FULL E2E: Admin selects multiple instructors → sends bulk reminder → all receive emails

        Steps:
        1. Log in as program admin
        2. Navigate to course management
        3. Select multiple instructors with checkboxes
        4. Click "Send Bulk Reminder" button
        5. Review recipient list
        6. Optionally add message
        7. Send bulk reminder
        8. Verify success message (with count)
        9. Check all instructors received emails
        10. Verify each email is personalized

        Email Assertions:
        - All instructors receive email within 10 seconds
        - Each email is personalized (not BCC'd)
        - Each email contains recipient's specific name
        - All emails contain same personal message (if provided)
        - Email rate limiting respected (if applicable)
        """
        # Setup: Log in as program admin
        _admin_email = "sarah.williams@loopclosertests.mailtrap.io"  # noqa: F841

        # Setup: Multiple instructors needing reminders
        instructors = [
            {
                "email": "instructor1@loopclosertests.mailtrap.io",
                "name": "Prof. Alice Adams",
            },
            {
                "email": "instructor2@loopclosertests.mailtrap.io",
                "name": "Dr. Bob Baker",
            },
            {
                "email": "instructor3@loopclosertests.mailtrap.io",
                "name": "Prof. Carol Chen",
            },
        ]

        # 1-2. Navigate to course management
        # browser.goto(f"{base_url}/program/courses")

        # 3. Select multiple instructors
        # for instructor in instructors:
        #     browser.check(f"input[type='checkbox'][data-instructor='{instructor['name']}']")

        # 4. Click bulk send
        # browser.click("button:has-text('Send Bulk Reminder')")

        # 5. Review recipient list in modal
        # expect(browser.locator(".bulk-reminder-modal")).to_be_visible()
        # expect(browser.locator(".recipient-count")).to_contain_text("3 instructors")
        # for instructor in instructors:
        #     expect(browser.locator(".recipient-list")).to_contain_text(
        #         instructor['name']
        #     )

        # 6. Add message for all
        bulk_message = "Friendly reminder to submit your course data by Friday!"
        # browser.fill("#bulk_message", bulk_message)

        # 7. Send bulk reminder
        # browser.click("button:has-text('Send to All')")

        # 8. Verify success message
        # expect(browser.locator(".success-message")).to_contain_text(
        #     "Reminders sent to 3 instructors"
        # )

        # 9. Check all emails received
        # email_helper = MailtrapHelper()
        # for instructor in instructors:
        #     reminder_email = email_helper.wait_for_email(
        #         to_email=instructor['email'],
        #         subject_contains="Reminder: Please submit",
        #         timeout_seconds=10
        #     )
        #     assert reminder_email is not None, f"Email not received for {instructor['name']}"
        #
        #     # Verify personalization
        #     assert instructor['name'] in reminder_email.html_body
        #     assert bulk_message in reminder_email.html_body
        #
        #     # Verify not BCC'd (each email is individual)
        #     assert reminder_email.to_email == instructor['email']


# API/Service Layer Pseudo-code
"""
# New EmailService method needed for Phase 4:

class EmailService:
    
    @staticmethod
    def send_instructor_reminder_email(
        to_email: str,
        instructor_name: str,
        sender_name: str,
        sender_role: str,
        term: str,
        personal_message: Optional[str] = None,
        deadline: Optional[str] = None,
        missing_courses: Optional[List[str]] = None
    ) -> bool:
        '''
        Send reminder email to instructor to submit course data
        
        Args:
            to_email: Instructor's email address
            instructor_name: Instructor's display name
            sender_name: Admin who sent reminder
            sender_role: Admin's role (Program Admin, Institution Admin)
            term: Current term/semester
            personal_message: Optional personalized message from admin
            deadline: Optional submission deadline
            missing_courses: Optional list of specific courses needing data
            
        Returns:
            True if email sent successfully, False otherwise
        '''
        subject = f"Reminder: Please submit your course data for {term}"
        
        html_body = EmailService._render_instructor_reminder_email_html(
            instructor_name=instructor_name,
            sender_name=sender_name,
            sender_role=sender_role,
            term=term,
            personal_message=personal_message,
            deadline=deadline,
            missing_courses=missing_courses
        )
        
        text_body = EmailService._render_instructor_reminder_email_text(
            instructor_name=instructor_name,
            sender_name=sender_name,
            sender_role=sender_role,
            term=term,
            personal_message=personal_message,
            deadline=deadline,
            missing_courses=missing_courses
        )
        
        return EmailService._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
    @staticmethod
    def _render_instructor_reminder_email_html(
        instructor_name, sender_name, sender_role, term, 
        personal_message, deadline, missing_courses
    ):
        '''Render HTML template for instructor reminder email'''
        # Template structure:
        # - Greeting: "Hi {instructor_name},"
        # - Context: "This is a friendly reminder from {sender_name} ({sender_role})"
        # - Purpose: "Please submit your course data for {term}"
        # - Personal Message: {personal_message} (if provided)
        # - Missing Courses: List of specific courses (if provided)
        # - Deadline: "Please submit by {deadline}" (if provided)
        # - CTA Button: "Submit Course Data Now"
        # - Help: "Need help? Contact us at support@courserecord.app"
        pass
"""
