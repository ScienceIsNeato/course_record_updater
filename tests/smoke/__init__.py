"""
Smoke Tests

Smoke tests are comprehensive end-to-end tests that verify the application works
as a whole. They are slower than unit and integration tests but provide confidence
that the entire system is functioning correctly.

These tests typically:
- Use real browsers (Selenium)
- Test complete user workflows
- Verify UI functionality
- Check cross-browser compatibility
- Validate performance under realistic conditions

Smoke tests are excluded from coverage reports and should be run separately
from unit tests during CI/CD pipelines.
"""
