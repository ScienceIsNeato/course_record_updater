"""
Unit tests for assessment page dirty tracking functionality.

Tests that the assessment page correctly detects unsaved changes
and doesn't show false positives when data has been loaded from the server.
"""

import pytest


class TestAssessmentDirtyTracking:
    """Test dirty tracking logic for assessment page"""

    def test_no_changes_after_load(self):
        """Should not detect changes when form values match loaded data"""
        loaded_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "Great engagement",
            "narrative_challenges": "Time management",
            "narrative_changes": "More examples",
        }

        current_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "Great engagement",
            "narrative_challenges": "Time management",
            "narrative_changes": "More examples",
        }

        has_changes = self._check_for_changes(loaded_data, current_data)
        assert has_changes is False, "Should not detect changes when data matches"

    def test_detects_text_field_change(self):
        """Should detect changes when text field is modified"""
        loaded_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "Great engagement",
            "narrative_challenges": "Time management",
            "narrative_changes": "More examples",
        }

        current_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "Great engagement",
            "narrative_challenges": "Time management issues",  # Changed
            "narrative_changes": "More examples",
        }

        has_changes = self._check_for_changes(loaded_data, current_data)
        assert has_changes is True, "Should detect text field change"

    def test_detects_number_field_change(self):
        """Should detect changes when number field is modified"""
        loaded_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        current_data = {
            "students_passed": "30",  # Changed
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        has_changes = self._check_for_changes(loaded_data, current_data)
        assert has_changes is True, "Should detect number field change"

    def test_detects_checkbox_change(self):
        """Should detect changes when checkbox is toggled"""
        loaded_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        current_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": True,  # Changed
            "reconciliation_note": "",
            "narrative_celebrations": "",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        has_changes = self._check_for_changes(loaded_data, current_data)
        assert has_changes is True, "Should detect checkbox change"

    def test_empty_to_empty_no_change(self):
        """Should not detect changes when both loaded and current are empty"""
        loaded_data = {
            "students_passed": "",
            "students_dfic": "",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        current_data = {
            "students_passed": "",
            "students_dfic": "",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        has_changes = self._check_for_changes(loaded_data, current_data)
        assert has_changes is False, "Should not detect changes when both are empty"

    def test_adding_new_data_is_change(self):
        """Should detect changes when adding data to empty fields"""
        loaded_data = {
            "students_passed": "",
            "students_dfic": "",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        current_data = {
            "students_passed": "25",  # Added
            "students_dfic": "",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        has_changes = self._check_for_changes(loaded_data, current_data)
        assert has_changes is True, "Should detect new data as change"

    def test_clearing_data_is_change(self):
        """Should detect changes when clearing previously filled fields"""
        loaded_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "Great",
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        current_data = {
            "students_passed": "25",
            "students_dfic": "5",
            "cannot_reconcile": False,
            "reconciliation_note": "",
            "narrative_celebrations": "",  # Cleared
            "narrative_challenges": "",
            "narrative_changes": "",
        }

        has_changes = self._check_for_changes(loaded_data, current_data)
        assert has_changes is True, "Should detect cleared data as change"

    def _check_for_changes(self, loaded_data, current_data):
        """
        Helper method that mimics the JavaScript checkForUnsavedChanges logic
        """
        return (
            current_data["students_passed"] != loaded_data["students_passed"]
            or current_data["students_dfic"] != loaded_data["students_dfic"]
            or current_data["cannot_reconcile"] != loaded_data["cannot_reconcile"]
            or current_data["reconciliation_note"] != loaded_data["reconciliation_note"]
            or current_data["narrative_celebrations"]
            != loaded_data["narrative_celebrations"]
            or current_data["narrative_challenges"]
            != loaded_data["narrative_challenges"]
            or current_data["narrative_changes"] != loaded_data["narrative_changes"]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
