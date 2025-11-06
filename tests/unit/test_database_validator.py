"""Tests for database schema validator."""

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.orm import DeclarativeMeta, declarative_base, registry

from database_validator import (
    SchemaValidationError,
    _get_model_columns,
    _get_table_columns,
    _suggest_similar_column,
    validate_schema,
    validate_schema_or_exit,
)


class TestColumnExtraction:
    """Test helper functions for extracting column information."""

    def test_get_model_columns(self):
        """Should extract column names from SQLAlchemy model."""
        TestBase = declarative_base()

        class TestModel(TestBase):  # type: ignore[misc,valid-type]
            __tablename__ = "test_table"
            id = Column(Integer, primary_key=True)
            name = Column(String)
            email = Column(String)

        columns = _get_model_columns(TestModel)
        assert columns == {"id", "name", "email"}

    def test_get_table_columns_from_inspector(self):
        """Should extract column names from database table via inspector."""
        # Create in-memory database with a test table
        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        Table(
            "test_table",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            Column("created_at", String),
        )
        metadata.create_all(engine)

        # Get columns via inspector
        from sqlalchemy import inspect

        inspector = inspect(engine)
        columns = _get_table_columns(inspector, "test_table")
        assert columns == {"id", "name", "created_at"}


class TestColumnSuggestions:
    """Test 'did you mean?' column name suggestions."""

    def test_suggest_exact_match_case_insensitive(self):
        """Should suggest exact match ignoring case."""
        available = {"email_verified", "is_active", "created_at"}
        suggestion = _suggest_similar_column("EMAIL_VERIFIED", available)
        assert suggestion == "email_verified"

    def test_suggest_contains_match(self):
        """Should suggest column name that contains the typo."""
        available = {"email_verified", "is_active", "created_at"}
        suggestion = _suggest_similar_column("email", available)
        assert suggestion == "email_verified"

    def test_suggest_is_contained_match(self):
        """Should suggest column name that is contained by the typo."""
        available = {"email", "is_active", "created_at"}
        suggestion = _suggest_similar_column("email_verified", available)
        assert suggestion == "email"

    def test_suggest_prefix_match(self):
        """Should suggest column with same prefix (4+ chars)."""
        available = {"email_verified", "email_sent_at", "is_active"}
        suggestion = _suggest_similar_column("email_confirm", available)
        assert suggestion in ["email_verified", "email_sent_at"]

    def test_suggest_none_for_no_match(self):
        """Should return None if no similar column found."""
        available = {"id", "name", "created_at"}
        suggestion = _suggest_similar_column("totally_different", available)
        assert suggestion is None

    def test_suggest_none_for_short_name(self):
        """Should return None for very short names (< 4 chars)."""
        available = {"id", "name", "age"}
        suggestion = _suggest_similar_column("xyz", available)
        assert suggestion is None


class TestSchemaValidation:
    """Test schema validation against actual database."""

    def test_validate_schema_success(self):
        """Should pass validation when schema matches."""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")

        # Create a test model that matches the database
        TestBase = declarative_base()

        class TestModel(TestBase):  # type: ignore[misc,valid-type]
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String)
            email = Column(String)

        # Create table in database
        TestBase.metadata.create_all(engine)

        # Create mock db_service
        class MockSQLite:
            def __init__(self):
                self.engine = engine

        class MockDBService:
            def __init__(self):
                self.sqlite = MockSQLite()

        # Temporarily replace Base with TestBase
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = MockDBService()
            issues = validate_schema(db_service, strict=True)
            assert issues == []
        finally:
            database_validator.Base = original_base

    def test_validate_schema_column_in_model_not_db(self):
        """Should detect column defined in model but missing in database."""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")

        # Create database table (missing 'age' column)
        metadata = MetaData()
        Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String),
        )
        metadata.create_all(engine)

        # Create model with extra column
        TestBase = declarative_base()

        class TestModel(TestBase):  # type: ignore[misc,valid-type]
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String)
            age = Column(Integer)  # This doesn't exist in DB

        # Create mock db_service
        class MockSQLite:
            def __init__(self):
                self.engine = engine

        class MockDBService:
            def __init__(self):
                self.sqlite = MockSQLite()

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = MockDBService()

            # Should raise error in strict mode
            with pytest.raises(SchemaValidationError) as exc_info:
                validate_schema(db_service, strict=True)

            assert "'age'" in str(exc_info.value)
            assert "not found in database" in str(exc_info.value)

            # Should return issues list in non-strict mode
            issues = validate_schema(db_service, strict=False)
            assert len(issues) == 1
            assert "'age'" in issues[0]
        finally:
            database_validator.Base = original_base

    def test_validate_schema_column_in_db_not_model(self):
        """Should warn about column in database but not in model."""
        # Create in-memory database with extra column
        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            Column("legacy_field", String),  # Extra column
        )
        metadata.create_all(engine)

        # Create model without legacy field
        TestBase = declarative_base()

        class TestModel(TestBase):  # type: ignore[misc,valid-type]
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        # Create mock db_service
        class MockSQLite:
            def __init__(self):
                self.engine = engine

        class MockDBService:
            def __init__(self):
                self.sqlite = MockSQLite()

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = MockDBService()

            # Should not raise in strict mode (warnings only for extra DB columns)
            issues = validate_schema(db_service, strict=True)

            # Should have warning about extra column
            assert len(issues) == 1
            assert "'legacy_field'" in issues[0]
            assert "⚠️" in issues[0]
            assert "not defined in" in issues[0]
        finally:
            database_validator.Base = original_base

    def test_validate_schema_table_missing_in_db(self):
        """Should detect when table is defined in model but missing in database."""
        # Create empty in-memory database
        engine = create_engine("sqlite:///:memory:")

        # Create model for non-existent table
        TestBase = declarative_base()

        class TestModel(TestBase):  # type: ignore[misc,valid-type]
            __tablename__ = "missing_table"
            id = Column(Integer, primary_key=True)

        # Create mock db_service
        class MockSQLite:
            def __init__(self):
                self.engine = engine

        class MockDBService:
            def __init__(self):
                self.sqlite = MockSQLite()

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = MockDBService()

            # Should raise error about missing table
            with pytest.raises(SchemaValidationError) as exc_info:
                validate_schema(db_service, strict=True)

            assert "missing_table" in str(exc_info.value)
            assert "not found in database" in str(exc_info.value)
        finally:
            database_validator.Base = original_base

    def test_validate_schema_or_exit_success(self):
        """Should succeed without raising when schema is valid."""
        # Create valid schema
        engine = create_engine("sqlite:///:memory:")
        TestBase = declarative_base()

        class TestModel(TestBase):  # type: ignore[misc,valid-type]
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        TestBase.metadata.create_all(engine)

        # Create mock db_service
        class MockSQLite:
            def __init__(self):
                self.engine = engine

        class MockDBService:
            def __init__(self):
                self.sqlite = MockSQLite()

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = MockDBService()
            # Should not raise
            validate_schema_or_exit(db_service)
        finally:
            database_validator.Base = original_base

    def test_validate_schema_or_exit_failure(self):
        """Should raise SchemaValidationError when schema is invalid."""
        # Create invalid schema (model has column DB doesn't)
        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))
        metadata.create_all(engine)

        TestBase = declarative_base()

        class TestModel(TestBase):  # type: ignore[misc,valid-type]
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            missing_col = Column(String)  # Not in DB

        # Create mock db_service
        class MockSQLite:
            def __init__(self):
                self.engine = engine

        class MockDBService:
            def __init__(self):
                self.sqlite = MockSQLite()

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = MockDBService()

            # Should raise
            with pytest.raises(SchemaValidationError):
                validate_schema_or_exit(db_service)
        finally:
            database_validator.Base = original_base

    def test_validate_schema_non_sqlite_backend(self):
        """Should handle non-SQLite database services gracefully."""

        # Create mock db_service without sqlite attribute
        class MockDBService:
            pass

        db_service = MockDBService()

        # Should not raise in non-strict mode
        issues = validate_schema(db_service, strict=False)
        assert len(issues) == 1
        assert "doesn't have expected SQLite backend" in issues[0]

        # Should raise AttributeError in strict mode
        with pytest.raises(AttributeError):
            validate_schema(db_service, strict=True)
