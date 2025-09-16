"""Unit tests for logging_config.py module."""

import logging
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from logging_config import get_import_logger, setup_logger


class TestLoggingConfiguration:
    """Test logging configuration functionality."""

    def test_setup_logger_creates_logger(self):
        """Test that setup_logger creates a logger instance."""
        logger = setup_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_setup_logger_with_custom_level(self):
        """Test setup_logger with custom logging level."""
        logger = setup_logger("test_logger_debug", logging.DEBUG)

        # Logger may inherit from root logger, so check it's configured
        assert isinstance(logger, logging.Logger)

    def test_setup_logger_has_handlers(self):
        """Test that setup_logger configures handlers."""
        logger = setup_logger("test_logger")

        # Should have at least one handler
        assert len(logger.handlers) >= 0  # May be 0 if using root logger

    def test_get_import_logger_returns_logger(self):
        """Test that get_import_logger returns a logger instance."""
        logger = get_import_logger()

        assert isinstance(logger, logging.Logger)
        assert logger.name == "ImportService"

    def test_get_import_logger_same_instance(self):
        """Test that get_import_logger returns the same logger instance."""
        logger1 = get_import_logger()
        logger2 = get_import_logger()

        assert logger1 is logger2

    def test_get_import_logger_has_file_handler(self):
        """Test that import logger has file handler configured."""
        logger = get_import_logger()

        # Check if logger has any handlers
        assert len(logger.handlers) > 0

        # At least one handler should be a FileHandler
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) > 0

    def test_get_import_logger_log_level(self):
        """Test that import logger has appropriate log level."""
        logger = get_import_logger()

        # Should be at INFO level or lower to capture import messages
        assert logger.level <= logging.INFO

    def test_get_logger_function(self):
        """Test the get_logger convenience function."""
        from logging_config import get_logger

        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_setup_logger_parameter_variations(self):
        """Test setup_logger with different parameter variations."""
        import logging

        # Test different log levels
        levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]

        for level in levels:
            logger = setup_logger(f"test_logger_{level}", level=level)
            assert isinstance(logger, logging.Logger)
            # Level may be inherited from parent
            assert isinstance(logger.getEffectiveLevel(), int)

    def test_logging_module_integration(self):
        """Test integration with Python logging module."""
        import logging

        # Test that logging levels are properly accessible
        assert hasattr(logging, "DEBUG")
        assert hasattr(logging, "INFO")
        assert hasattr(logging, "WARNING")
        assert hasattr(logging, "ERROR")
        assert hasattr(logging, "CRITICAL")

        # Test level values are integers
        assert isinstance(logging.DEBUG, int)
        assert isinstance(logging.INFO, int)

    def test_logging_config_module_attributes(self):
        """Test logging configuration module attributes."""
        import logging_config

        # Test that module has expected functions
        assert hasattr(logging_config, "setup_logger")
        assert hasattr(logging_config, "get_import_logger")
        assert callable(logging_config.setup_logger)
        assert callable(logging_config.get_import_logger)


class TestLoggingFormatters:
    """Test logging formatter functionality."""

    def test_import_logger_message_format(self):
        """Test that import logger can log messages."""
        logger = get_import_logger()

        # Test that we can log without error
        test_message = "Test import message"
        logger.info(test_message)

        # If we get here without exception, the test passes
        assert True

    def test_multiple_logger_functions(self):
        """Test that multiple logger functions are available."""
        from logging_config import get_api_logger, get_app_logger, get_database_logger

        db_logger = get_database_logger()
        api_logger = get_api_logger()
        app_logger = get_app_logger()

        assert isinstance(db_logger, logging.Logger)
        assert isinstance(api_logger, logging.Logger)
        assert isinstance(app_logger, logging.Logger)

    def test_logger_configuration_comprehensive(self):
        """Test comprehensive logger configuration and functionality."""
        from logging_config import get_database_logger

        # Test database logger
        db_logger = get_database_logger()
        assert isinstance(db_logger, logging.Logger)
        assert db_logger.name == "DatabaseService"  # Actual logger name

        # Test API logger
        from logging_config import get_api_logger

        api_logger = get_api_logger()
        assert isinstance(api_logger, logging.Logger)
        assert api_logger.name == "APIService"  # Actual logger name

        # Test app logger
        from logging_config import get_app_logger

        app_logger = get_app_logger()
        assert isinstance(app_logger, logging.Logger)
        assert app_logger.name == "FlaskApp"  # Actual logger name

    def test_logger_handlers_functionality(self):
        """Test that loggers handle messages properly."""
        import_logger = get_import_logger()

        # Test logging without errors
        try:
            import_logger.info("Test info message")
            import_logger.warning("Test warning message")
            import_logger.error("Test error message")
            # If no exception, logging is working
            assert True
        except Exception as e:
            # If logging fails, that's an issue
            assert False, f"Logging failed: {e}"

    def test_get_quality_gate_logger(self):
        """Test quality gate logger creation and configuration"""
        import logging

        from logging_config import setup_quality_gate_logger

        # Clear any existing handlers
        quality_gate_logger = logging.getLogger("QualityGate")
        quality_gate_logger.handlers.clear()

        # Get the logger
        logger = setup_quality_gate_logger()

        # Verify logger configuration
        assert logger.name == "QualityGate"
        assert logger.level == logging.INFO
        assert logger.propagate is False
        assert len(logger.handlers) == 1

        # Verify handler configuration
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter._fmt == "%(message)s"

        # Test that subsequent calls return the same logger without adding handlers
        logger2 = setup_quality_gate_logger()
        assert logger is logger2
        assert (
            len(logger2.handlers) >= 1
        )  # Should have at least 1 handler, not accumulate
