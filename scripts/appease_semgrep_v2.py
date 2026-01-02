import os
import re

js_files = ["static/institution_dashboard.js", "static/program_dashboard.js"]


def refactor_empty_state_usage(content):
    # Match pattern with line breaks
    pattern = re.compile(
        r'(?://\s*nosemgrep\s*\n\s*)?([\w.]+)\.innerHTML\s*=\s*this\.renderEmptyState\(\s*\n\s*(["\'])(.*?)\2,\s*\n\s*(["\'])(.*?)\4,?\s*\n\s*\);(?:\s*//\s*nosemgrep)?',
        re.DOTALL,
    )

    def replacer(match):
        container = match.group(1)
        arg1 = match.group(3)
        arg2 = match.group(5)
        return f'{container}.innerHTML = "";\n        {container}.appendChild(this.renderEmptyState("{arg1}", "{arg2}"));'

    return pattern.sub(replacer, content)


for file_path in js_files:
    if not os.path.exists(file_path):
        continue
    print(f"Refactoring {file_path}...")
    with open(file_path, "r") as f:
        content = f.read()

    # 1. Update renderEmptyState definition to return Element
    old_def = 'renderEmptyState(message, actionLabel) {\n      return `\n        <div class="panel-empty">\n          <div class="panel-empty-icon">📌</div>\n          <p>${message}</p>\n          <button class="btn btn-primary btn-sm" onclick="return false;">${actionLabel}</button>\n        </div>\n      `;\n    },'
    new_def = 'renderEmptyState(message, actionLabel) {\n      const wrapper = document.createElement("div");\n      wrapper.className = "panel-empty";\n      const icon = document.createElement("div");\n      icon.className = "panel-empty-icon";\n      icon.textContent = "📌";\n      const p = document.createElement("p");\n      p.textContent = message;\n      const button = document.createElement("button");\n      button.className = "btn btn-primary btn-sm";\n      button.textContent = actionLabel;\n      button.onclick = () => false;\n      wrapper.appendChild(icon);\n      wrapper.appendChild(p);\n      wrapper.appendChild(button);\n      return wrapper;\n    },'

    if old_def in content:
        content = content.replace(old_def, new_def)
        print(f"Updated definition in {file_path}")

    # 2. Refactor usages
    new_content = refactor_empty_state_usage(content)

    with open(file_path, "w") as f:
        f.write(new_content)
