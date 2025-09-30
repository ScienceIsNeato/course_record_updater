"""
Global pytest configuration for course record updater.

This file provides pytest fixtures and configuration that are available
to all test modules.
"""

import os

import pytest

# Configure environment for testing
os.environ["WTF_CSRF_ENABLED"] = "false"  # Disable CSRF for testing
