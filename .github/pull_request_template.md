## Description

<!-- Describe what this PR does and why -->

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🧹 Code cleanup/refactoring (no functional changes)
- [ ] 🧪 Test improvements

## Test Review Checklist

<!-- These checks help ensure test quality and prevent coverage-padding -->

- [ ] New tests have **meaningful assertions** (not just imports or coverage-padding)
- [ ] No `time.sleep()` without justification (use mocking or async waits instead)
- [ ] Fixtures are **appropriately scoped** (session/module for expensive setup, function for isolation)
- [ ] Coverage increase comes from testing **behavior**, not just executing lines
- [ ] Tests are **deterministic** (no flaky tests that depend on timing or external state)

## Quality Checklist

- [ ] I have run `python scripts/ship_it.py --checks commit` and all checks pass
- [ ] My changes follow the existing code style (Black, isort, flake8)
- [ ] I have added/updated tests that cover my changes
- [ ] I have updated documentation if needed
- [ ] My changes do not introduce new security vulnerabilities

## Related Issues

<!-- Link any related issues: Fixes #123, Relates to #456 -->

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

## Additional Notes

<!-- Any additional context or notes for reviewers -->
