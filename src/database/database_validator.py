"""Database schema validation utility for Course Record Updater.

This module validates that SQLAlchemy models match the actual database schema,
catching column name typos and schema mismatches at startup before they cause
runtime errors.

Note: This validator is SQLAlchemy-specific and works with any database backend
that uses SQLAlchemy (SQLite, PostgreSQL, MySQL, etc.). It accesses the database
through SQLAlchemy's inspector API, not through DatabaseInterface.
"""

from __future__ import annotations

import logging
from typing import Any, List, Set

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeMeta

from src.models.models_sql import Base

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Raised when database schema doesn't match SQLAlchemy models."""

    pass


def _get_model_columns(model: DeclarativeMeta) -> Set[str]:
    """Extract column names from SQLAlchemy model.

    Args:
        model: SQLAlchemy model class

    Returns:
        Set of column names defined in the model
    """
    mapper = inspect(model)
    return {col.key for col in mapper.columns}


def _get_table_columns(inspector: Any, table_name: str) -> Set[str]:
    """Extract column names from database table via SQLAlchemy inspector.

    Args:
        inspector: SQLAlchemy inspector instance
        table_name: Name of the database table

    Returns:
        Set of column names in the actual database table
    """
    columns = inspector.get_columns(table_name)
    return {col["name"] for col in columns}


def _get_sqlalchemy_engine(db_service: Any) -> Any:
    """Extract SQLAlchemy engine from database service.

    Works with any database implementation that uses SQLAlchemy and exposes
    the engine (e.g., SQLiteDatabase via sqlite.engine).

    Args:
        db_service: Database service instance

    Returns:
        SQLAlchemy engine instance

    Raises:
        AttributeError: If db_service doesn't have SQLAlchemy engine
    """
    # Try common patterns for accessing SQLAlchemy engine
    # SQLiteDatabase: db_service.sqlite.engine
    # Other implementations might expose engine differently
    if hasattr(db_service, "sqlite") and hasattr(db_service.sqlite, "engine"):
        return db_service.sqlite.engine

    # Try direct engine attribute
    if hasattr(db_service, "engine"):
        return db_service.engine

    raise AttributeError(
        f"Database service {type(db_service).__name__} doesn't expose SQLAlchemy engine. "
        "Schema validation requires SQLAlchemy-based database implementation."
    )


def _get_all_models() -> List[Any]:
    """Get all SQLAlchemy models from Base registry.

    Returns:
        List of model classes
    """
    models = []
    try:
        # Try to get models from registry (SQLAlchemy 1.4+)
        if hasattr(Base, "registry"):
            for mapper in Base.registry.mappers:  # type: ignore[attr-defined]
                models.append(mapper.class_)
        else:
            # Fallback: get from _decl_class_registry (older SQLAlchemy)
            models = list(Base._decl_class_registry.values())  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        # If registry access fails, log warning
        logger.warning("Could not access model registry, using metadata approach")
        # This won't validate as thoroughly but better than nothing
        for table_name in Base.metadata.tables:
            logger.info(f"Found table in metadata: {table_name}")
    return models


def _validate_table_exists(
    inspector: Any, model: Any, strict: bool
) -> tuple[List[str], bool]:
    """Validate that a table exists in the database.

    Returns:
        Tuple of (issues list, should_continue)
    """
    issues = []
    table_name = model.__tablename__

    if table_name not in inspector.get_table_names():
        issue = (
            f"❌ Table '{table_name}' defined in model {model.__name__} "
            f"but not found in database"
        )
        issues.append(issue)
        logger.error(issue)
        if strict:
            raise SchemaValidationError(issue)
        return issues, False

    return issues, True


def _validate_model_columns(inspector: Any, model: Any, strict: bool) -> List[str]:
    """Validate that model columns match database columns.

    Returns:
        List of validation issues
    """
    issues = []
    table_name = model.__tablename__

    # Get column names from model and database
    model_columns = _get_model_columns(model)
    db_columns = _get_table_columns(inspector, table_name)

    # Find columns that exist in model but not in database
    missing_in_db = model_columns - db_columns
    for col_name in missing_in_db:
        issue = (
            f"❌ Column '{col_name}' defined in {model.__name__} model "
            f"but not found in database table '{table_name}'."
        )
        issues.append(issue)
        logger.error(issue)
        if strict:
            raise SchemaValidationError(issue)

    # Find columns that exist in database but not in model (warning only)
    missing_in_model = db_columns - model_columns
    for col_name in missing_in_model:
        warning = (
            f"⚠️  Column '{col_name}' exists in database table '{table_name}' "
            f"but not defined in {model.__name__} model. "
            f"This may be intentional (deprecated column) or an oversight."
        )
        issues.append(warning)
        logger.warning(warning)

    return issues


def validate_schema(db_service: Any, strict: bool = True) -> List[str]:
    """Validate that SQLAlchemy models match database schema.

    Compares the columns defined in SQLAlchemy models against the actual
    columns in the database tables. Reports any mismatches with clear
    error messages.

    Note: This function is SQLAlchemy-specific and works with any database
    backend that uses SQLAlchemy (SQLite, PostgreSQL, MySQL, etc.).

    Args:
        db_service: Database service instance (must use SQLAlchemy)
        strict: If True, raise exception on first mismatch. If False,
                collect all issues and return as list.

    Returns:
        List of validation warnings/errors (empty if all valid)

    Raises:
        SchemaValidationError: If strict=True and schema mismatch found
        AttributeError: If db_service doesn't expose SQLAlchemy engine
    """
    issues: List[str] = []

    # Get SQLAlchemy engine from service
    try:
        engine = _get_sqlalchemy_engine(db_service)
    except AttributeError as e:
        error_msg = (
            f"Schema validation requires SQLAlchemy-based database: {e}. "
            "This validator works with SQLite, PostgreSQL, MySQL, and other "
            "SQLAlchemy-supported backends."
        )
        if strict:
            raise AttributeError(error_msg) from e
        logger.warning(error_msg)
        return [error_msg]

    # Create inspector
    inspector = inspect(engine)

    # Get all models
    models = _get_all_models()

    # Validate each model
    for model in models:
        # Skip non-model entries (like '_sa_module_registry')
        if not hasattr(model, "__tablename__"):
            continue

        # Validate table exists
        table_issues, should_continue = _validate_table_exists(inspector, model, strict)
        issues.extend(table_issues)
        if not should_continue:
            continue

        # Validate columns
        column_issues = _validate_model_columns(inspector, model, strict)
        issues.extend(column_issues)

    if not issues:
        logger.info("✅ Database schema validation passed - all models match database")

    return issues


def validate_schema_or_exit(db_service: Any) -> None:
    """Validate schema and exit if validation fails.

    This is the recommended function to call at application startup.
    Will log clear error messages and raise exception if schema is invalid.

    Args:
        db_service: Database service instance

    Raises:
        SchemaValidationError: If schema validation fails
        SystemExit: If validation fails (prevents startup)
    """
    logger.info("🔍 Validating database schema...")

    try:
        issues = validate_schema(db_service, strict=True)
        if issues:
            # Should never reach here if strict=True, but just in case
            logger.error("Database schema validation found issues:")
            for issue in issues:
                logger.error(f"  {issue}")
            raise SchemaValidationError(
                f"Found {len(issues)} schema validation issue(s). "
                "Fix schema mismatches before starting the application."
            )
    except SchemaValidationError:
        logger.error(
            "⛔ Application startup blocked due to schema validation failure. "
            "Please fix the schema mismatches above before restarting."
        )
        raise
    except Exception as e:
        # Unexpected errors should also block startup - don't silently proceed
        logger.error(
            f"⛔ Schema validation encountered unexpected error: {e}. "
            "Application startup blocked. Fix the validation error before restarting."
        )
        raise SchemaValidationError(
            f"Schema validation failed with unexpected error: {e}"
        ) from e
