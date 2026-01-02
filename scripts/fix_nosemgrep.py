import os
import re

js_files = [
    "static/audit_clo.js",
    "static/institution_dashboard.js",
    "static/instructor_dashboard.js",
    "static/program_dashboard.js",
    "static/courseManagement.js",
    "static/script.js",
    "static/panels.js",
]

for file_path in js_files:
    if not os.path.exists(file_path):
        print(f"Skipping {file_path}")
        continue
    with open(file_path, "r") as f:
        content = f.read()

    # Move nosemgrep from end to before for multiline statements

    # Match .innerHTML = ... ); // nosemgrep
    pattern = re.compile(
        r"(\n\s*)(\w+\.innerHTML\s*=\s*(?:[^\n]*\n)*?.*?);\s*//\s*nosemgrep", re.DOTALL
    )
    content = pattern.sub(r"\1// nosemgrep\1\2;", content)

    # Match console.warn( ... ); // nosemgrep
    pattern_warn = re.compile(
        r"(\n\s*)(console\.warn\s*\(\s*(?:[^\n]*\n)*?.*?)\);?\s*//\s*nosemgrep",
        re.DOTALL,
    )
    content = pattern_warn.sub(r"\1// nosemgrep\1\2);", content)

    # Some might already have // nosemgrep before but still have it at the end
    # Clean up double nosemgrep if they exist
    content = content.replace("// nosemgrep\n        // nosemgrep", "// nosemgrep")

    with open(file_path, "w") as f:
        f.write(content)
    print(f"Processed {file_path}")
