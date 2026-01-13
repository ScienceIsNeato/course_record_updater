"""
Tests for term status calculation with the "holds active" behavior.

The "holds active" rule: A term remains ACTIVE even after its end_date passes,
UNTIL another term's start_date has also passed. This prevents a gap where
no term appears active during the transition period between semesters.

Example scenario (reference date: Dec 23, 2025):
- Fall 2025: Aug 29 - Dec 14, 2025 → Should be ACTIVE (Spring 2026 hasn't started yet)
- Spring 2025: Jan 9 - May 14, 2025 → Should be PASSED (Fall 2025 took over)
- Spring 2026: Jan 12 - May 8, 2026 → Should be SCHEDULED (hasn't started)
"""

from datetime import date

from src.utils.term_utils import (
    TERM_STATUS_ACTIVE,
    TERM_STATUS_PASSED,
    TERM_STATUS_SCHEDULED,
    get_all_term_statuses,
    get_term_status_with_context,
)


class TestTermStatusHoldsActive:
    """Tests for the 'holds active until successor starts' behavior."""

    def test_term_stays_active_after_end_date_when_no_successor_started(self):
        """
        Fall 2025 ends Dec 14, 2025. On Dec 23, 2025, it should still be ACTIVE
        because Spring 2026 (the next term) hasn't started yet.
        """
        reference_date = date(2025, 12, 23)

        terms = [
            {
                "term_id": "fall-2025",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
            {
                "term_id": "spring-2026",
                "start_date": "2026-01-12",
                "end_date": "2026-05-08",
            },
        ]

        statuses = get_all_term_statuses(terms, reference_date)

        assert statuses["fall-2025"] == TERM_STATUS_ACTIVE
        assert statuses["spring-2026"] == TERM_STATUS_SCHEDULED

    def test_term_becomes_passed_when_successor_starts(self):
        """
        Fall 2025 ends Dec 14, 2025. On Jan 15, 2026 (after Spring 2026 starts),
        Fall 2025 should be PASSED and Spring 2026 should be ACTIVE.
        """
        reference_date = date(2026, 1, 15)

        terms = [
            {
                "term_id": "fall-2025",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
            {
                "term_id": "spring-2026",
                "start_date": "2026-01-12",
                "end_date": "2026-05-08",
            },
        ]

        statuses = get_all_term_statuses(terms, reference_date)

        assert statuses["fall-2025"] == TERM_STATUS_PASSED
        assert statuses["spring-2026"] == TERM_STATUS_ACTIVE

    def test_older_term_is_passed_when_newer_term_has_started(self):
        """
        Spring 2025 should be PASSED on Dec 23, 2025 because Fall 2025 already started.
        """
        reference_date = date(2025, 12, 23)

        terms = [
            {
                "term_id": "spring-2025",
                "start_date": "2025-01-09",
                "end_date": "2025-05-14",
            },
            {
                "term_id": "fall-2025",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
        ]

        statuses = get_all_term_statuses(terms, reference_date)

        assert statuses["spring-2025"] == TERM_STATUS_PASSED
        assert statuses["fall-2025"] == TERM_STATUS_ACTIVE

    def test_multiple_past_terms_only_most_recent_is_active(self):
        """
        With multiple past terms, only the most recently ended (without successor)
        should be ACTIVE.
        """
        reference_date = date(2025, 12, 23)

        terms = [
            {
                "term_id": "spring-2025",
                "start_date": "2025-01-09",
                "end_date": "2025-05-14",
            },
            {
                "term_id": "summer-2025",
                "start_date": "2025-05-20",
                "end_date": "2025-08-15",
            },
            {
                "term_id": "fall-2025",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
            {
                "term_id": "spring-2026",
                "start_date": "2026-01-12",
                "end_date": "2026-05-08",
            },
        ]

        statuses = get_all_term_statuses(terms, reference_date)

        assert statuses["spring-2025"] == TERM_STATUS_PASSED
        assert statuses["summer-2025"] == TERM_STATUS_PASSED
        assert (
            statuses["fall-2025"] == TERM_STATUS_ACTIVE
        )  # Most recent, no successor started
        assert statuses["spring-2026"] == TERM_STATUS_SCHEDULED

    def test_term_within_dates_is_always_active(self):
        """
        A term is ACTIVE if the reference date is within its start/end dates,
        regardless of other terms.
        """
        reference_date = date(2025, 10, 15)  # Middle of Fall 2025

        terms = [
            {
                "term_id": "fall-2025",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
        ]

        statuses = get_all_term_statuses(terms, reference_date)

        assert statuses["fall-2025"] == TERM_STATUS_ACTIVE

    def test_future_term_is_scheduled(self):
        """A term that hasn't started yet is SCHEDULED."""
        reference_date = date(2025, 12, 23)

        terms = [
            {
                "term_id": "spring-2026",
                "start_date": "2026-01-12",
                "end_date": "2026-05-08",
            },
        ]

        statuses = get_all_term_statuses(terms, reference_date)

        assert statuses["spring-2026"] == TERM_STATUS_SCHEDULED

    def test_single_term_status_with_context(self):
        """Test getting a single term's status with context of all terms."""
        reference_date = date(2025, 12, 23)

        all_terms = [
            {
                "term_id": "fall-2025",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
            {
                "term_id": "spring-2026",
                "start_date": "2026-01-12",
                "end_date": "2026-05-08",
            },
        ]

        # Fall 2025 should be ACTIVE since Spring 2026 hasn't started
        status = get_term_status_with_context(
            start_date="2025-08-29",
            end_date="2025-12-14",
            all_terms=all_terms,
            reference_date=reference_date,
        )

        assert status == TERM_STATUS_ACTIVE

    def test_overlapping_terms_both_active(self):
        """
        If two terms overlap (e.g., short session within a semester),
        both can be ACTIVE at the same time.
        """
        reference_date = date(2025, 10, 15)

        terms = [
            {
                "term_id": "fall-2025",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
            {
                "term_id": "fall-2025-short",
                "start_date": "2025-10-01",
                "end_date": "2025-10-31",
            },
        ]

        statuses = get_all_term_statuses(terms, reference_date)

        assert statuses["fall-2025"] == TERM_STATUS_ACTIVE
        assert statuses["fall-2025-short"] == TERM_STATUS_ACTIVE

    def test_handles_missing_dates_gracefully(self):
        """Terms with missing dates should have UNKNOWN status handled appropriately."""
        reference_date = date(2025, 12, 23)

        terms = [
            {
                "term_id": "valid-term",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
            {"term_id": "missing-dates", "start_date": None, "end_date": None},
        ]

        statuses = get_all_term_statuses(terms, reference_date)

        # Valid term should still work correctly
        assert statuses["valid-term"] == TERM_STATUS_ACTIVE
        # Missing dates term gets UNKNOWN
        assert statuses["missing-dates"] == "UNKNOWN"

    def test_uses_get_current_time_when_no_reference_date(self):
        """When no reference date is provided, should use get_current_time()."""
        terms = [
            {
                "term_id": "fall-2025",
                "start_date": "2025-08-29",
                "end_date": "2025-12-14",
            },
        ]

        # This should not raise and should use the current time
        statuses = get_all_term_statuses(terms)
        assert "fall-2025" in statuses
