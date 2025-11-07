"""Tests for database schema validator.

This test suite includes:
- Generic validator tests (column extraction, error handling)
- SQLAlchemy-specific integration tests
"""

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.orm import declarative_base

from database_validator import (
    SchemaValidationError,
    _get_model_columns,
    _get_table_columns,
    validate_schema,
    validate_schema_or_exit,
)


class TestColumnExtraction:
    """Test helper functions for extracting column information (generic)."""

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
        """Should extract column names from database table via inspector (SQLAlchemy-specific)."""
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


class TestSQLAlchemySchemaValidation:
    """SQLAlchemy-specific schema validation tests."""

    def _create_db_service_with_engine(self, engine):
        """Create a db_service-like object with SQLAlchemy engine."""

        # Simple object that mimics SQLiteDatabase structure
        class Service:
            def __init__(self, engine):
                self.sqlite = type("SQLite", (), {"engine": engine})()

        return Service(engine)

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

        # Temporarily replace Base with TestBase
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = self._create_db_service_with_engine(engine)
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

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = self._create_db_service_with_engine(engine)

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

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = self._create_db_service_with_engine(engine)

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

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = self._create_db_service_with_engine(engine)

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

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = self._create_db_service_with_engine(engine)
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

        # Temporarily replace Base
        import database_validator

        original_base = database_validator.Base
        database_validator.Base = TestBase

        try:
            db_service = self._create_db_service_with_engine(engine)

            # Should raise
            with pytest.raises(SchemaValidationError):
                validate_schema_or_exit(db_service)
        finally:
            database_validator.Base = original_base

    def test_validate_schema_non_sqlalchemy_backend(self):
        """Should handle non-SQLAlchemy database services gracefully."""

        # Create service without SQLAlchemy engine
        class NonSQLAlchemyService:
            pass

        db_service = NonSQLAlchemyService()

        # Should not raise in non-strict mode
        issues = validate_schema(db_service, strict=False)
        assert len(issues) == 1
        assert "doesn't expose SQLAlchemy engine" in issues[0]

        # Should raise AttributeError in strict mode
        with pytest.raises(AttributeError):
            validate_schema(db_service, strict=True)

    def test_get_sqlalchemy_engine_direct_engine_attribute(self):
        """Should handle db_service with direct engine attribute."""
        engine = create_engine("sqlite:///:memory:")

        # Create service with direct engine attribute
        class DirectEngineService:
            def __init__(self, engine):
                self.engine = engine

        db_service = DirectEngineService(engine)

        from database_validator import _get_sqlalchemy_engine

        result_engine = _get_sqlalchemy_engine(db_service)
        assert result_engine is engine

    def test_get_all_models_fallback_to_metadata(self):
        """Should fallback to metadata approach when registry access fails."""
        import database_validator
        from database_validator import _get_all_models

        # Mock Base to raise AttributeError when accessing registry
        original_base = database_validator.Base

        class MockBase:
            metadata = original_base.metadata
            registry = None  # Simulate missing registry

        # Temporarily replace Base
        database_validator.Base = MockBase  # type: ignore[assignment]

        try:
            # Should not raise, should fallback to metadata
            models = _get_all_models()
            # Should return empty list or handle gracefully
            assert isinstance(models, list)
        finally:
            database_validator.Base = original_base

    def test_validate_table_exists_table_missing(self):
        """Should return issues and should_continue=False when table missing."""
        from sqlalchemy import inspect

        from database_validator import _validate_table_exists

        engine = create_engine("sqlite:///:memory:")
        inspector = inspect(engine)

        # Create a mock model for non-existent table
        class MockModel:
            __tablename__ = "nonexistent_table"
            __name__ = "MockModel"

        model = MockModel()

        # Should return issues and False
        issues, should_continue = _validate_table_exists(inspector, model, strict=False)
        assert len(issues) > 0
        assert "nonexistent_table" in issues[0]
        assert should_continue is False

    def test_validate_model_columns_db_columns_not_in_model(self):
        """Should return warnings for columns in DB but not in model."""
        from sqlalchemy import inspect

        from database_validator import _validate_model_columns

        engine = create_engine("sqlite:///:memory:")
        inspector = inspect(engine)

        # Create table with extra column
        TestBase = declarative_base()

        class TestModel(TestBase):  # type: ignore[misc,valid-type]
            __tablename__ = "test_table"
            id = Column(Integer, primary_key=True)
            name = Column(String)
            # Missing 'extra_column' that exists in DB

        # Create table with extra column
        from sqlalchemy import Column as TableColumn
        from sqlalchemy import MetaData, Table

        metadata = MetaData()
        Table(
            "test_table",
            metadata,
            TableColumn("id", Integer, primary_key=True),
            TableColumn("name", String),
            TableColumn("extra_column", String),  # Extra column in DB
        )
        metadata.create_all(engine)

        # Should return warnings
        issues = _validate_model_columns(inspector, TestModel, strict=False)
        assert len(issues) > 0
        assert any("extra_column" in issue for issue in issues)
        assert any("⚠️" in issue for issue in issues)  # Should be warnings, not errors

    def test_validate_schema_or_exit_unexpected_error(self):
        """Should raise SchemaValidationError for unexpected errors."""
        import database_validator
        from database_validator import SchemaValidationError, validate_schema_or_exit

        # Create service that will cause unexpected error
        class BrokenService:
            def __getattr__(self, name):
                raise RuntimeError("Unexpected error")

        db_service = BrokenService()

        # Should raise SchemaValidationError wrapping the unexpected error
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_or_exit(db_service)

        assert "Unexpected error" in str(exc_info.value)
