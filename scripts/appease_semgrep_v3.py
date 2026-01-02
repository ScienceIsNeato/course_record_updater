import os
import re

js_files = [
    "static/institution_dashboard.js",
    "static/instructor_dashboard.js",
    "static/program_dashboard.js",
]


def refactor_empty_state_usage(content):
    # Match pattern: innerHTML = this.renderEmptyState(...) optionally with comments
    # We use non-greedy matching for the arguments, careful with nested parens
    # Since renderEmptyState doesn't have nested parens in args, this is safe
    pattern = re.compile(
        r"([\w.]+)\.innerHTML\s*=\s*this\.renderEmptyState\((.*?)\);", re.DOTALL
    )

    def replacer(match):
        container = match.group(1)
        args = match.group(2).strip()
        return f'{container}.innerHTML = ""; {container}.appendChild(this.renderEmptyState({args}));'

    # Clean up nosemgrep comments
    content = re.sub(r"//\s*nosemgrep\s*", "", content)

    return pattern.sub(replacer, content)


for file_path in js_files:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r") as f:
        content = f.read()

    new_content = refactor_empty_state_usage(content)

    with open(file_path, "w") as f:
        f.write(new_content)
