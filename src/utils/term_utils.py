"""
Term utilities for dynamic academic term generation.
Replaces hardcoded ALLOWED_TERMS with flexible term management.
"""

from datetime import date, datetime
from typing import List, Optional, Union

from src.utils.time_utils import get_current_time


class TermGenerator:
    """Generates academic terms dynamically based on current date and rules."""

    # Term configurations
    TERM_CODES = {"FA": "Fall", "SP": "Spring", "SU": "Summer"}

    def __init__(
        self,
        base_year: Optional[int] = None,
        years_forward: int = 2,
        years_back: int = 1,
    ):
        """
        Initialize term generator.

        Args:
            base_year: Base year for term generation (defaults to current year)
            years_forward: How many years ahead to generate terms
            years_back: How many years back to generate terms
        """
        self.base_year = base_year or datetime.now().year
        self.years_forward = years_forward
        self.years_back = years_back

    def get_valid_terms(self) -> List[str]:
        """
        Generate list of valid academic terms.

        Returns:
            List of term codes (e.g., ['FA2024', 'SP2025', 'SU2025'])
        """
        terms = []

        # Generate terms for the specified year range
        start_year = self.base_year - self.years_back
        end_year = self.base_year + self.years_forward

        for year in range(start_year, end_year + 1):
            for term_code in self.TERM_CODES.keys():
                terms.append(f"{term_code}{year}")

        return sorted(terms)

    def is_valid_term(self, term: str) -> bool:
        """
        Check if a term is valid.

        Args:
            term: Term code to validate (e.g., 'FA2024')

        Returns:
            True if term is valid, False otherwise
        """
        return term in self.get_valid_terms()

    def get_current_term(self) -> str:
        """
        Get the current academic term based on today's date.

        Returns:
            Current term code (e.g., 'FA2024')
        """
        now = datetime.now()
        year = now.year
        month = now.month

        # Academic year logic:
        # Spring: January - May (same calendar year)
        # Summer: June - August (same calendar year)
        # Fall: September - December (same calendar year)
        if 1 <= month <= 5:
            return f"SP{year}"
        elif 6 <= month <= 8:
            return f"SU{year}"
        else:  # 9-12
            return f"FA{year}"

    def get_term_display_name(self, term: str) -> str:
        """
        Get human-readable display name for a term.

        Args:
            term: Term code (e.g., 'FA2024')

        Returns:
            Display name (e.g., 'Fall 2024')
        """
        if len(term) < 6:
            return term  # Return as-is if not in expected format

        term_code = term[:2]
        year = term[2:]

        term_name = self.TERM_CODES.get(term_code, term_code)
        return f"{term_name} {year}"

    @classmethod
    def get_default_terms(cls) -> List[str]:
        """
        Get default terms for backward compatibility.

        Returns:
            List of default valid terms
        """
        generator = cls()
        return generator.get_valid_terms()


# Global instances for easy access
default_term_generator = TermGenerator()


def get_allowed_terms() -> List[str]:
    """Get currently allowed terms (backward compatibility function)."""
    return default_term_generator.get_valid_terms()


def is_valid_term(term: str) -> bool:
    """Check if term is valid (backward compatibility function)."""
    return default_term_generator.is_valid_term(term)


def get_current_term() -> str:
    """Get current academic term (convenience function)."""
    return default_term_generator.get_current_term()


def get_term_display_name(term: str) -> str:
    """Get human-readable display name for a term (convenience function)."""
    return default_term_generator.get_term_display_name(term)


# ---------------------------------------------------------------------------
# Term status helpers
# ---------------------------------------------------------------------------

TERM_STATUS_PASSED = "PASSED"
TERM_STATUS_ACTIVE = "ACTIVE"
TERM_STATUS_SCHEDULED = "SCHEDULED"
TERM_STATUS_UNKNOWN = "UNKNOWN"


def _coerce_to_date(value: Union[str, datetime, date, None]) -> Optional[date]:
    """Convert ISO string/datetime/date to a date object."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    try:
        # Attempt to parse full ISO string first
        return datetime.fromisoformat(value).date()
    except (TypeError, ValueError):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None


def get_term_status(
    start_date: Union[str, datetime, date, None],
    end_date: Union[str, datetime, date, None],
    reference_date: Optional[date] = None,
) -> str:
    """
    Compute a term's status.

    Returns:
        PASSED | ACTIVE | SCHEDULED | UNKNOWN
    """
    start = _coerce_to_date(start_date)
    end = _coerce_to_date(end_date)
    ref = reference_date or get_current_time().date()

    if not start or not end:
        return TERM_STATUS_UNKNOWN

    if ref < start:
        return TERM_STATUS_SCHEDULED
    if ref > end:
        return TERM_STATUS_PASSED
    return TERM_STATUS_ACTIVE


def is_term_active(
    start_date: Union[str, datetime, date, None],
    end_date: Union[str, datetime, date, None],
    reference_date: Optional[date] = None,
) -> bool:
    """Return True if the term is currently active."""
    return get_term_status(start_date, end_date, reference_date) == TERM_STATUS_ACTIVE
