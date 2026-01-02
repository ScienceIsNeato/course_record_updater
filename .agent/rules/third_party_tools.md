---
trigger: always_on
description: "Antigravity rule"
---
# Third Party Tools Integration Rules

## Google Calendar Integration

### Tool Location
- Script: `cursor-rules/scripts/gcal_utils.py`
- Authentication: Uses Application Default Credentials (ADC)
- Prerequisite: User must have run `gcloud auth application-default login`

### Calendar Event Workflow
1. **Date Context**: For relative dates ("tomorrow", "next Friday"), run `date` command first
2. **Required Fields**: Title/Summary, Date, Start Time
3. **Defaults**: 1-hour duration, single day, timezone from `date` command or UTC
4. **Processing**: Convert to ISO 8601 format, use `%%NL%%` for newlines in descriptions
5. **Execution**: Create immediately without confirmation, provide event link

### Command Syntax
**Base**: `cd ${AGENT_HOME} && python cursor-rules/scripts/gcal_utils.py`

**Actions**: `add` (create), `update` (modify), `list` (view)

**Key Parameters**: 
- `--summary`, `--description`, `--start_time`, `--end_time` (ISO 8601)
- `--timezone`, `--attendees`, `--update_if_exists` (for create)
- `--event_id` (for update), `--max_results` (for list)

**Notes**: Times in ISO 8601, outputs event link, uses 'primary' calendar

## Markdown to PDF Conversion

### Tool Location
- Script: `cursor-rules/scripts/md_to_pdf.py` (requires Chrome/Chromium)
- Execution: `cd ${AGENT_HOME}/cursor-rules/scripts && source .venv/bin/activate && python md_to_pdf.py`

### Usage
- **Basic**: `python md_to_pdf.py ../../document.md`
- **Options**: `--html-only`, `--keep-html`, specify output file
- **Features**: Professional styling, cross-platform, print optimization

## JIRA Integration

### Tool Location
- Script: `cursor-rules/scripts/jira_utils.py`
- Auth: Environment variables (`JIRA_SERVER`, `JIRA_USERNAME`, `JIRA_API_TOKEN`)
- Epic storage: `data/epic_keys.json`

### Usage
**Base**: `cd ${AGENT_HOME} && python cursor-rules/scripts/jira_utils.py`

**Actions**:
- `--action create_epic`: `--summary`, `--description`, `--epic-actual-name`
- `--action create_task`: `--epic-name`, `--summary`, `--description`, `--issue-type`
- `--action update_issue`: `--issue-key`, `--fields` (JSON)

**Notes**: Project key "MARTIN", epic mappings auto-saved

## GitHub Integration

### Integration Strategy (Updated Nov 2025)

**PRIMARY METHOD**: Use standardized scripts that abstract gh CLI details

**DEPRECATED**: GitHub MCP server (causes 7000+ line payloads that crash Cursor on PR comment retrieval)

### PR Status Checking (STANDARD WORKFLOW)

**After pushing to PR - Use watch mode to eliminate manual checking:**

```bash
cd ${AGENT_HOME} && python3 cursor-rules/scripts/pr_status.py --watch [PR_NUMBER]
```

**Watch mode behavior:**
- Polls CI status every 30 seconds
- Shows progress updates when status changes
- **Automatically reports results when CI completes**
- No human intervention needed
- Ctrl+C to cancel

**Single status check (when CI already complete):**

```bash
cd ${AGENT_HOME} && python3 cursor-rules/scripts/pr_status.py [PR_NUMBER]
```

**What it provides:**
- PR overview (commits, lines changed, files)
- Latest commit info
- CI status (running/failed/passed)
- **Failed checks with direct links**
- In-progress checks with elapsed time
- Next steps guidance

**Exit codes:**
- `0` - All checks passed (ready to merge)
- `1` - Checks failed or in progress
- `2` - Error (no PR found, gh CLI missing)

**Workflow Integration:**
1. Make changes and commit
2. Push to PR
3. **Immediately run `--watch` mode** (no waiting for human)
4. Script polls CI automatically
5. When CI completes, results appear
6. If failures, address them immediately
7. Repeat until all green

**Benefits:**
- **Eliminates idle waiting time**
- **No manual "is CI done?" checking**
- Consistent output format
- Abstraction layer hides gh CLI complexity
- Single source of truth for PR workflow

### PR Comment Review Protocol (gh CLI)

**Step 1: Get PR number**
```bash
gh pr view --json number,title,url
```

**Step 2: Fetch PR comments and reviews**
```bash
# Get general comments and reviews
gh pr view <PR_NUMBER> --comments --json comments,reviews | jq '.'

# Get inline review comments (code-level)
gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/comments --jq '.[] | {path: .path, line: .line, body: .body, id: .id}'
```

**Step 3: Strategic Analysis**
Group comments by underlying concept (not by file location):
- Security issues
- Export functionality
- Parsing/validation
- Test quality
- Performance

**Step 4: Address systematically**
Prioritize by risk/impact (CRITICAL > HIGH > MEDIUM > LOW)

**Step 5: Reply to comments**
```bash
# Create comment file
cat > /tmp/pr_comment.md << 'EOF'
## Response to feedback...
EOF

# Post comment
gh pr comment <PR_NUMBER> --body-file /tmp/pr_comment.md
```

### Common gh CLI Commands

**Pull Requests:**
- View PR: `gh pr view <NUMBER>`
- List PRs: `gh pr list`
- Create PR: `gh pr create --title "..." --body "..."`
- Check status: `gh pr status`

**Issues:**
- Create: `gh issue create --title "..." --body-file /tmp/issue.md`
- List: `gh issue list`
- View: `gh issue view <NUMBER>`

**Repository:**
- Clone: `gh repo clone <OWNER>/<REPO>`
- View: `gh repo view`
- Create: `gh repo create`

### Benefits of gh CLI
- Handles large payloads without crashing
- Direct JSON output with `jq` integration
- No MCP server overhead
- Reliable authentication via `gh auth login`
- Native markdown file support (`--body-file`)
