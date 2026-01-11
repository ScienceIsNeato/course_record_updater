"""SQLite engine and session management for LoopCloser."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from src.models.models_sql import Base


class SQLiteService:
    """Manage SQLite engine and sessions."""

    def __init__(self, db_path: str | None = None) -> None:
        db_url = db_path or os.getenv("DATABASE_URL", "sqlite:///course_records.db")
        assert db_url is not None, "DATABASE_URL must be set"
        connect_args = (
            {"check_same_thread": False} if db_url.startswith("sqlite") else {}
        )
        self.engine = create_engine(
            db_url, future=True, echo=False, connect_args=connect_args
        )
        Base.metadata.create_all(self.engine)
        self._session_factory = scoped_session(
            sessionmaker(bind=self.engine, expire_on_commit=False, autoflush=False)
        )

    def get_session(self) -> Any:
        return self._session_factory()

    def remove_session(self) -> None:
        self._session_factory.remove()

    @contextmanager
    def session_scope(self) -> Iterator:
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Dispose of the engine and connection pool."""
        self._session_factory.remove()
        self.engine.dispose()
