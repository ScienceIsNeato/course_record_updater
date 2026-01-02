---
trigger: always_on
description: "These rules should befollowed whenever tests are being run"
---

# Testing Protocol 🧪

## Test Execution Guidelines

### Core Rules
- Do not interrupt tests unless test cases have failed
- Run tests in the Composer window
- Wait for test completion before proceeding unless failures occur
- Ensure all test output is visible and accessible
- Stop tests immediately upon failure to investigate
- Always retest after making changes to fix failures

### Best Practices
- Monitor test execution actively
- Keep test output visible
- Address failures immediately
- Document any unexpected behavior
- Maintain clear test logs

## Failure Response Protocol

### When Tests Fail
1. Stop test execution immediately
2. Investigate failure cause
3. Document the failure context
4. Make necessary fixes
5. Rerun tests to verify fix

### Test Output Management
- Keep test output accessible
- Document any error messages
- Save relevant logs
- Track test execution time

## Coverage Strategy Reference

See development_workflow.mdc for strategic coverage improvement guidelines including:
- Priority-based coverage strategy (new/modified code first)
- Big wins approach for contiguous uncovered blocks
- Extending existing tests rather than creating single-purpose error tests