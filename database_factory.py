"""Database service factory for selecting backend implementation."""

from __future__ import annotations

import os
from functools import lru_cache

from database_interface import DatabaseInterface
from database_sqlite import SQLiteDatabase


@lru_cache(maxsize=1)
def get_database_service() -> DatabaseInterface:
    """Return configured database service instance."""
    db_type = os.getenv("DATABASE_TYPE", "sqlite").lower()
    if db_type in {"sqlite", "sql"}:
        return SQLiteDatabase(os.getenv("DATABASE_URL"))
    raise ValueError(f"Unsupported DATABASE_TYPE: {db_type}")


# Convenience singleton used by modules expecting attribute access
_db_service = get_database_service()


def refresh_database_service() -> DatabaseInterface:
    """Reset cached database service (useful for tests)."""
    get_database_service.cache_clear()  # type: ignore[attr-defined]
    return get_database_service()


__all__ = ["get_database_service", "refresh_database_service", "_db_service"]
