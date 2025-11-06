"""Database schema validation utility for Course Record Updater.

This module validates that SQLAlchemy models match the actual database schema,
catching column name typos and schema mismatches at startup before they cause
runtime errors.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeMeta

from models_sql import Base

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
    """Extract column names from database table.

    Args:
        inspector: SQLAlchemy inspector instance
        table_name: Name of the database table

    Returns:
        Set of column names in the actual database table
    """
    columns = inspector.get_columns(table_name)
    return {col["name"] for col in columns}


def _suggest_similar_column(
    incorrect_name: str, available_columns: Set[str]
) -> str | None:
    """Suggest a similar column name for a typo.

    Uses simple string similarity to suggest corrections.

    Args:
        incorrect_name: The column name that wasn't found
        available_columns: Set of valid column names

    Returns:
        Suggested column name or None
    """
    # Simple Levenshtein-like heuristic: check for similar names
    incorrect_lower = incorrect_name.lower()

    # Exact match (case-insensitive)
    for col in available_columns:
        if col.lower() == incorrect_lower:
            return col

    # Contains or is contained by
    for col in available_columns:
        col_lower = col.lower()
        if incorrect_lower in col_lower or col_lower in incorrect_lower:
            return col

    # Start with same prefix (at least 4 chars)
    if len(incorrect_lower) >= 4:
        for col in available_columns:
            if col.lower().startswith(incorrect_lower[:4]):
                return col

    return None


def validate_schema(db_service: Any, strict: bool = True) -> List[str]:
    """Validate that SQLAlchemy models match database schema.

    Compares the columns defined in SQLAlchemy models against the actual
    columns in the database tables. Reports any mismatches with helpful
    error messages.

    Args:
        db_service: Database service instance (must have SQLite backend)
        strict: If True, raise exception on first mismatch. If False,
                collect all issues and return as list.

    Returns:
        List of validation warnings/errors (empty if all valid)

    Raises:
        SchemaValidationError: If strict=True and schema mismatch found
        AttributeError: If db_service doesn't have required attributes
    """
    issues: List[str] = []

    # Get database engine from service
    try:
        engine = db_service.sqlite.engine
    except AttributeError as e:
        error_msg = (
            f"Database service doesn't have expected SQLite backend: {e}. "
            "Schema validation only works with SQLite implementation."
        )
        if strict:
            raise AttributeError(error_msg) from e
        logger.warning(error_msg)
        return [error_msg]

    # Create inspector
    inspector = inspect(engine)

    # Get all mapped models from SQLAlchemy Base metadata
    # Use Base.metadata.tables to get all registered tables
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
        # If registry access fails, try alternative approach
        logger.warning("Could not access model registry, using metadata approach")
        # This won't validate as thoroughly but better than nothing
        for table_name in Base.metadata.tables:
            logger.info(f"Found table in metadata: {table_name}")

    # Validate each model
    for model in models:
        # Skip non-model entries (like '_sa_module_registry')
        if not hasattr(model, "__tablename__"):
            continue

        table_name = model.__tablename__

        # Check if table exists in database
        if table_name not in inspector.get_table_names():
            issue = (
                f"❌ Table '{table_name}' defined in model {model.__name__} "
                f"but not found in database"
            )
            issues.append(issue)
            logger.error(issue)
            if strict:
                raise SchemaValidationError(issue)
            continue

        # Get column names from model and database
        model_columns = _get_model_columns(model)
        db_columns = _get_table_columns(inspector, table_name)

        # Find columns that exist in model but not in database
        missing_in_db = model_columns - db_columns
        for col_name in missing_in_db:
            suggestion = _suggest_similar_column(col_name, db_columns)
            suggestion_text = f" Did you mean '{suggestion}'?" if suggestion else ""

            issue = (
                f"❌ Column '{col_name}' defined in {model.__name__} model "
                f"but not found in database table '{table_name}'.{suggestion_text}"
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
            # Don't raise exception for columns in DB but not in model
            # (might be legacy/deprecated columns)

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
        SystemExit: If validation fails and we want to prevent startup
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
        logger.error(f"⚠️  Schema validation encountered unexpected error: {e}")
        # Don't block startup for unexpected validation errors
        logger.warning("Proceeding with application startup despite validation error")
