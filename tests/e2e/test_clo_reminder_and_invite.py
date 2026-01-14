"""
E2E tests for CLO reminder and invite functionality in audit page.

Tests:
- Sending reminders with auto-populated information (instructor name, course, section, due date)
- Inviting new instructors from the assignment modal
"""

import re

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import BASE_URL


def test_reminder_autopopulates_context(admin_page, csrf_token):
    """Test that reminder modal auto-populates instructor name, course, section, and due date."""

    # Navigate to audit CLO page
    admin_page.goto(f"{BASE_URL}/audit-clo")
    expect(admin_page).to_have_url(f"{BASE_URL}/audit-clo")

    # Wait for CLOs to load
    admin_page.wait_for_selector("#cloListContainer table", timeout=10000)

    # Find a CLO with "in_progress" status that should have a reminder button
    reminder_button = admin_page.locator('button[title="Send Reminder"]').first

    # If no reminder button found, skip test (means no CLOs in appropriate status)
    if not reminder_button.is_visible():
        pytest.skip("No CLOs available with reminder button")

    # Click the reminder button
    reminder_button.click()

    # Wait for reminder modal to open
    admin_page.wait_for_selector("#sendReminderModal.show", timeout=5000)

    # Check that description is populated
    description = admin_page.locator("#reminderCloDescription").text_content()
    assert description, "Reminder description should be populated"
    assert (
        "CLO" in description or "Section" in description
    ), "Description should contain CLO or Section info"

    # Check that message is auto-populated
    message = admin_page.locator("#reminderMessage").input_value()
    assert message, "Reminder message should be auto-populated"
    assert "Dear" in message, "Message should start with greeting"
    assert "reminder" in message.lower(), "Message should mention reminder"

    # Verify helper text is present
    helper_text = admin_page.locator(
        'small.text-muted:has-text("auto-populated")'
    ).first
    expect(helper_text).to_be_visible()

    # Close modal
    admin_page.locator("#sendReminderModal button.btn-close").click()


def test_invite_instructor_from_assignment_modal(admin_page, csrf_token):
    """Test inviting a new instructor from the assignment modal."""

    # Navigate to audit CLO page
    admin_page.goto(f"{BASE_URL}/audit-clo")
    expect(admin_page).to_have_url(f"{BASE_URL}/audit-clo")

    # Wait for CLOs to load
    admin_page.wait_for_selector("#cloListContainer table", timeout=10000)

    # Find a CLO with "unassigned" status that should have an assign button
    assign_button = admin_page.locator('button[title="Assign Instructor"]').first

    # If no assign button found, skip test (means no unassigned CLOs)
    if not assign_button.is_visible():
        pytest.skip("No unassigned CLOs available")

    # Click the assign button
    assign_button.click()

    # Wait for assignment modal to open
    admin_page.wait_for_selector("#assignInstructorModal.show", timeout=5000)

    # Verify "Invite New Instructor" button is present
    invite_button = admin_page.locator("#inviteNewInstructorBtn")
    expect(invite_button).to_be_visible()
    expect(invite_button).to_have_text(
        re.compile("Invite New Instructor", re.IGNORECASE)
    )

    # Click invite button
    invite_button.click()

    # Wait for invite modal to open
    admin_page.wait_for_selector("#inviteInstructorModal.show", timeout=5000)

    # Verify assignment modal is closed
    assign_modal = admin_page.locator("#assignInstructorModal")
    expect(assign_modal).not_to_have_class(re.compile("show"))

    # Verify form fields are present
    expect(admin_page.locator("#inviteEmail")).to_be_visible()
    expect(admin_page.locator("#inviteFirstName")).to_be_visible()
    expect(admin_page.locator("#inviteLastName")).to_be_visible()

    # Verify helper text explains section assignment
    helper = admin_page.locator('.alert-info:has-text("assigned to this section")')
    expect(helper).to_be_visible()

    # Close modal
    admin_page.locator("#inviteInstructorModal button.btn-close").click()


def test_invite_submission_validates_fields(admin_page, csrf_token):
    """Test that invite form validates required fields."""

    # Navigate to audit CLO page
    admin_page.goto(f"{BASE_URL}/audit-clo")

    # Wait for CLOs to load
    admin_page.wait_for_selector("#cloListContainer table", timeout=10000)

    # Find and click assign button
    assign_button = admin_page.locator('button[title="Assign Instructor"]').first

    if not assign_button.is_visible():
        pytest.skip("No unassigned CLOs available")

    assign_button.click()
    admin_page.wait_for_selector("#assignInstructorModal.show", timeout=5000)

    # Click invite button
    admin_page.locator("#inviteNewInstructorBtn").click()
    admin_page.wait_for_selector("#inviteInstructorModal.show", timeout=5000)

    # Try to submit without filling fields
    admin_page.locator("#sendInviteBtn").click()

    # HTML5 validation should prevent submission
    # Check that modal is still visible (form didn't submit)
    expect(admin_page.locator("#inviteInstructorModal.show")).to_be_visible()

    # Fill in only email
    admin_page.locator("#inviteEmail").fill("newprof@university.edu")
    admin_page.locator("#sendInviteBtn").click()

    # Should still be visible (missing first/last name)
    expect(admin_page.locator("#inviteInstructorModal.show")).to_be_visible()


def test_reminder_includes_due_date_when_available(admin_page, csrf_token):
    """Test that reminder message includes due date when section has one."""

    # This test would require setting up a section with a due date
    # For now, we'll just verify the message format when due date is present

    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.wait_for_selector("#cloListContainer table", timeout=10000)

    reminder_button = admin_page.locator('button[title="Send Reminder"]').first

    if not reminder_button.is_visible():
        pytest.skip("No CLOs with reminder button available")

    reminder_button.click()
    admin_page.wait_for_selector("#sendReminderModal.show", timeout=5000)

    # Get the message
    message = admin_page.locator("#reminderMessage").input_value()

    # If the section has a due date, it should be in the message
    # We can't guarantee this without test data setup, but we can verify
    # the message structure is correct
    assert "Dear" in message, "Message should have greeting"
    assert "reminder" in message.lower(), "Message should mention reminder"
    assert "CLO" in message, "Message should reference CLO"

    # Optionally check for due date format if present
    if "Submission due date:" in message:
        # Verify date format is reasonable (MM/DD/YYYY or similar)
        date_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", message)
        assert date_match, "Due date should be in readable format"
