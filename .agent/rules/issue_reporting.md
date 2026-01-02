---
trigger: always_on
description: "Rules for issue reporting and tracking"
---
# Issue Reporting Protocol 🐛

## Information Gathering

### Issue Types
- **bug**: A problem with existing functionality
- **enhancement**: A new feature or improvement
- **documentation**: Documentation-related issues
- **test**: Test-related issues
- **ci**: CI/CD pipeline issues

### Required Information
1. Issue Type (from above list)
2. Clear, concise title summarizing the issue
3. Detailed description following template

## Description Template

```markdown
### Current Behavior
[What is happening now]

### Expected Behavior
[What should happen instead]

### Steps to Reproduce (if applicable)
1. [First Step]
2. [Second Step]
3. [...]

### Additional Context
- Environment: [e.g., local/CI, OS, relevant versions]
- Related Components: [e.g., TTV, Tests, Music Generation]
- Impact Level: [low/medium/high]
```

## Issue Creation Process

### Steps
1. **Prepare the Issue Content**: Write the content in Markdown and save it to a temporary Markdown file (`/tmp/issue_body.md`).
2. **Create the Issue Using `gh` CLI**: Use the `gh issue create` command with the `--body-file` option to specify the path of the Markdown file. For example:
   ```bash
   gh issue create --title "TITLE" --body-file "/tmp/issue_body.md" --label "TYPE"
   ```
3. **Delete the Markdown File** (Optional): Remove the file after creation to clean up the `/tmp/` directory.
4. **Display Created Issue URL**

This method prevents formatting issues in GitHub CLI submissions and ensures the integrity of the issue's formatting.

## Example Usage

### Sample Issue Creation
```bash
gh issue create \
  --title "Video credits abruptly cut off at 30 seconds in integration tests" \
  --body "### Current Behavior
Credits section in generated videos is being cut off at exactly 30 seconds during integration tests.

### Expected Behavior
Credits should play completely without being cut off.

### Steps to Reproduce
1. Run integration tests
2. Check generated video output
3. Observe credits section ending abruptly at 30s mark

### Additional Context
- Environment: CI pipeline
- Related Components: TTV, Integration Tests
- Impact Level: medium" \
  --label "bug"
```

## Best Practices
- Be specific and clear in descriptions
- Include all necessary context
- Use appropriate labels
- Link related issues if applicable
- Follow template structure consistently
