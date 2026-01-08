"""Database service factory for selecting backend implementation."""

from __future__ import annotations

import logging
import os
import threading
from functools import lru_cache

from src.database.database_interface import DatabaseInterface
from src.database.database_sqlite import SQLiteDatabase

_cached_db_service: DatabaseInterface | None = None
_cached_db_url: str | None = None
_cache_lock = threading.Lock()


def get_database_service() -> DatabaseInterface:
    """Return configured database service instance.

    Uses a thread-safe cache that invalidates when DATABASE_URL changes.
    This ensures we don't create multiple database instances in a single
    process, but also allows for database URL changes (e.g., in tests).
    """
    global _cached_db_service, _cached_db_url

    db_type = os.getenv("DATABASE_TYPE", "sqlite").lower()
    current_db_url = os.getenv("DATABASE_URL")

    # Thread-safe cache check and creation
    with _cache_lock:
        # If URL changed, invalidate cache
        if current_db_url != _cached_db_url:
            _cached_db_service = None
            _cached_db_url = current_db_url

        # Return cached instance if available
        if _cached_db_service is not None:
            return _cached_db_service

        # Create new instance
        if db_type in {"sqlite", "sql"}:
            _cached_db_service = SQLiteDatabase(current_db_url)
            return _cached_db_service
        raise ValueError(f"Unsupported DATABASE_TYPE: {db_type}")


# Convenience singleton used by modules expecting attribute access
_db_service = get_database_service()


def refresh_database_service() -> DatabaseInterface:
    """Reset cached database service (useful for tests)."""
    global _cached_db_service, _cached_db_url
    _cached_db_service = None
    _cached_db_url = None
    return get_database_service()


__all__ = ["get_database_service", "refresh_database_service", "_db_service"]
