"""Shared helpers for the SQLAlchemy-backed database implementation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple


def _ensure_uuid(value: Optional[str]) -> str:
    return value or str(uuid.uuid4())


TERM_STATUS_FIELDS: Tuple[str, ...] = ("active", "is_active", "status")
OFFERING_STATUS_FIELDS: Tuple[str, ...] = (
    "status",
    "term_status",
    "timeline_status",
    "is_active",
    "active",
)
SECTION_DATETIME_FIELDS: Tuple[str, ...] = (
    "due_date",
    "assigned_date",
    "completed_date",
)


def _remove_fields(payload: Dict[str, Any], keys: Tuple[str, ...]) -> None:
    """Remove status-ish fields from payload dictionaries to avoid persistence."""
    for key in keys:
        payload.pop(key, None)


def _normalize_section_datetime(value: Any) -> Any:
    """Convert section datetime inputs into native datetime objects."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            try:
                parsed = datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return value
        if isinstance(parsed, date) and not isinstance(parsed, datetime):
            parsed = datetime.combine(parsed, datetime.min.time())
        return parsed
    return value
