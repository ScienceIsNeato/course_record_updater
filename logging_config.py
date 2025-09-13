"""
Centralized Logging Configuration for Course Record Updater

This module provides consistent logging setup across all modules in the project.
It ensures uniform formatting, levels, and handler configuration.
"""

import logging
import sys
from pathlib import Path


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create a standardized logger for the Course Record Updater project.

    Args:
        name: Logger name (typically __name__ or module-specific name)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding multiple handlers if logger already exists
    if logger.handlers:
        return logger

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create file handler (logs directory)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "application.log", mode="a")
    file_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set formatter for handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(level)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False

    return logger


def setup_quality_gate_logger() -> logging.Logger:
    """
    Create a specialized logger for quality gate operations.
    Uses simpler formatting for better readability during quality checks.

    Returns:
        Configured quality gate logger
    """
    logger = logging.getLogger("QualityGate")

    if logger.handlers:
        return logger

    # Console handler with simple format for quality gate output
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(message)s")  # Simple format for quality gate
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with standardized configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return setup_logger(name)


# Module-specific logger shortcuts for common use cases
def get_database_logger() -> logging.Logger:
    """Get logger for database operations."""
    return setup_logger("DatabaseService")


def get_import_logger() -> logging.Logger:
    """Get logger for import operations."""
    return setup_logger("ImportService")


def get_api_logger() -> logging.Logger:
    """Get logger for API operations."""
    return setup_logger("APIService")


def get_app_logger() -> logging.Logger:
    """Get logger for Flask application."""
    return setup_logger("FlaskApp")
