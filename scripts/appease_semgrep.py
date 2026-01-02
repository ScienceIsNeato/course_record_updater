import os
import re

js_files = [
    "static/institution_dashboard.js",
    "static/instructor_dashboard.js",
    "static/program_dashboard.js",
]


def refactor_empty_state_usage(content):
    # Match pattern:
    # (// nosemgrep\n)?
    # any_container.innerHTML = this.renderEmptyState(
    #   "message",
    #   "label"
    # ); (// nosemgrep)?

    # Regex for the pattern, handling whitespace and optional comments
    pattern = re.compile(
        r'(?://\s*nosemgrep\n\s*)?([\w.]+)\.innerHTML\s*=\s*this\.renderEmptyState\(\s*(["\'])(.*?)\2,\s*(["\'])(.*?)\4\s*\);(?:\s*//\s*nosemgrep)?',
        re.DOTALL,
    )

    def replacer(match):
        container = match.group(1)
        arg1 = match.group(3)
        arg2 = match.group(5)
        # Indents are tricky, we'll try to preserve them roughly
        return f'{container}.innerHTML = "";\n        {container}.appendChild(this.renderEmptyState("{arg1}", "{arg2}"));'

    return pattern.sub(replacer, content)


for file_path in js_files:
    if not os.path.exists(file_path):
        continue
    print(f"Refactoring {file_path}...")
    with open(file_path, "r") as f:
        content = f.read()

    new_content = refactor_empty_state_usage(content)

    with open(file_path, "w") as f:
        f.write(new_content)
