#!/usr/bin/env python3
"""
Generate comprehensive route inventory for UI exploration.

Extracts all routes from:
- app.py (Flask app routes)
- api_routes.py (legacy monolithic API)
- api/routes/*.py (modular API blueprints)

Organizes by:
- Route path
- HTTP methods
- Authentication requirements
- Permission requirements
- Template files
- Role access
"""

import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

# Role hierarchy for access determination
ROLES = ["site_admin", "institution_admin", "program_admin", "instructor"]


class RouteExtractor(ast.NodeVisitor):
    """AST visitor to extract route decorators and function metadata."""

    def __init__(self):
        self.routes = []
        self.current_function = None
        self.current_decorators = []

    def visit_FunctionDef(self, node):
        """Visit function definitions to extract route decorators."""
        self.current_function = node.name
        self.current_decorators = []

        # Extract decorators
        for decorator in node.decorator_list:
            self.visit(decorator)

        # Store route info if we found a route decorator
        if self.current_decorators:
            for route_info in self.current_decorators:
                route_info["function_name"] = self.current_function
                route_info["docstring"] = ast.get_docstring(node) or ""
                self.routes.append(route_info)

        self.generic_visit(node)

    def visit_Call(self, node):
        """Extract route decorator calls."""
        if isinstance(node.func, ast.Attribute):
            # Handle @app.route, @api.route, @blueprint.route
            if node.func.attr == "route":
                route_path = None
                methods = ["GET"]

                # Extract route path (first positional argument)
                if node.args and isinstance(node.args[0], ast.Constant):
                    route_path = node.args[0].value

                # Extract methods from keyword arguments
                for keyword in node.keywords:
                    if keyword.arg == "methods":
                        if isinstance(keyword.value, ast.List):
                            methods = [
                                elt.value
                                for elt in keyword.value.elts
                                if isinstance(elt, ast.Constant)
                            ]

                self.current_decorators.append(
                    {
                        "path": route_path,
                        "methods": methods,
                    }
                )

        self.generic_visit(node)


def extract_routes_from_file(file_path: Path) -> List[Dict]:
    """Extract routes from a Python file using AST parsing."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        extractor = RouteExtractor()
        extractor.visit(tree)

        # Add file context to routes
        for route in extractor.routes:
            route["source_file"] = str(file_path)

        return extractor.routes
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def extract_routes_regex(file_path: Path) -> List[Dict]:
    """Extract route decorators using regex."""
    routes = []
    seen_routes = set()  # Track unique routes to avoid duplicates

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Process line by line to avoid matching in comments/strings
        for i, line in enumerate(lines):
            # Skip comments and docstrings
            stripped = line.strip()
            if (
                stripped.startswith("#")
                or stripped.startswith('"""')
                or stripped.startswith("'''")
            ):
                continue

            # Pattern for @app.route, @api.route, @blueprint.route, etc.
            # Match only at start of line (after whitespace) to avoid matches in strings
            pattern = (
                r'@(\w+)\.route\(["\']([^"\']+)["\'](?:\s*,\s*methods=\[([^\]]+)\])?\)'
            )

            match = re.search(pattern, line)
            if match:
                blueprint_name = match.group(1)
                route_path = match.group(2)
                methods_str = match.group(3) if match.group(3) else None

                # Parse methods
                if methods_str:
                    methods = [
                        m.strip().strip('"').strip("'") for m in methods_str.split(",")
                    ]
                else:
                    methods = ["GET"]

                # Create unique key to avoid duplicates
                route_key = (route_path, tuple(sorted(methods)))
                if route_key not in seen_routes:
                    seen_routes.add(route_key)

                    # Find function name (next def after this decorator)
                    function_name = None
                    for j in range(i + 1, min(i + 10, len(lines))):
                        func_match = re.search(r"def\s+(\w+)", lines[j])
                        if func_match:
                            function_name = func_match.group(1)
                            break

                    routes.append(
                        {
                            "path": route_path,
                            "methods": methods,
                            "blueprint": blueprint_name,
                            "source_file": str(file_path),
                            "function_name": function_name,
                            "line_number": i + 1,
                        }
                    )
    except Exception as e:
        print(f"Error extracting routes from {file_path}: {e}")

    return routes


def get_blueprint_prefix(file_path: Path) -> str:
    """Determine blueprint URL prefix from file."""
    if "api/routes" in str(file_path):
        # Check the blueprint definition
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Look for url_prefix in Blueprint definition
                match = re.search(
                    r'Blueprint\([^,]+,\s*url_prefix=["\']([^"\']+)["\']', content
                )
                if match:
                    return match.group(1)
        except Exception:  # nosec B110 - fallback if file parsing fails
            pass

    return ""


def extract_auth_requirements(file_path: Path, function_name: str) -> Dict[str, Any]:
    """Extract authentication and permission requirements from file."""
    auth_info: Dict[str, Any] = {
        "login_required": False,
        "permission_required": None,
        "has_permission_check": False,
    }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find the function
        in_function = False
        for i, line in enumerate(lines):
            if f"def {function_name}" in line:
                in_function = True
                # Check decorators above function
                j = i - 1
                while j >= 0 and lines[j].strip().startswith("@"):
                    decorator = lines[j].strip()
                    if "@login_required" in decorator:
                        auth_info["login_required"] = True
                    elif "@permission_required" in decorator:
                        # Extract permission name
                        match = re.search(
                            r'@permission_required\(["\']([^"\']+)["\']\)', decorator
                        )
                        if match:
                            auth_info["permission_required"] = str(match.group(1))
                    j -= 1

                # Check function body for has_permission checks
                for k in range(i, min(i + 50, len(lines))):
                    if "has_permission" in lines[k]:
                        auth_info["has_permission_check"] = True
                        break
                break
    except Exception as e:
        print(f"Error extracting auth requirements: {e}")

    return auth_info


def map_route_to_template(route_path: str, source_file: str) -> str:
    """Map route path to template file."""
    # Map known routes to templates
    template_map = {
        "/": "splash.html",
        "/login": "auth/login.html",
        "/reminder-login": "auth/login.html",
        "/register": "auth/register.html",
        "/register/accept/<token>": "auth/register_invitation.html",
        "/forgot-password": "auth/forgot_password.html",
        "/reset-password/<token>": "auth/reset_password.html",
        "/profile": "auth/profile.html",
        "/admin/users": "admin/user_management.html",
        "/dashboard": "dashboard/{role}.html",  # Role-specific
        "/courses": "courses_list.html",
        "/users": "users_list.html",
        "/assessments": "assessments.html",
        "/audit-clo": "audit_clo.html",
        "/sections": "sections_list.html",
    }

    # Check exact match first
    if route_path in template_map:
        return template_map[route_path]

    # Check pattern matches
    for pattern, template in template_map.items():
        if "<" in pattern:
            base_pattern = pattern.split("<")[0]
            if route_path.startswith(base_pattern):
                return template

    return ""


def _determine_api_role_access(route_path, auth_info):
    """Determine role access for API routes."""
    # Health check is public
    if route_path == "/api/health" or route_path.endswith("/health"):
        return ["public"]

    # Auth routes are public
    if "/auth/" in route_path or route_path.startswith("/api/auth/"):
        if (
            "login" in route_path
            or "register" in route_path
            or "forgot-password" in route_path
        ):
            return ["public"]

    # Most API routes require login
    if auth_info["login_required"]:
        if auth_info["permission_required"] == "manage_users":
            return ["site_admin"]
        elif auth_info["permission_required"] == "audit_clo":
            return ["institution_admin", "program_admin"]
        else:
            # Default: all authenticated roles
            return ["site_admin", "institution_admin", "program_admin", "instructor"]

    return ["public"]


def _determine_page_role_access(route_path, auth_info):
    """Determine role access for page routes."""
    if route_path in ["/", "/login", "/register"]:
        return ["public"]

    if route_path == "/admin/users":
        return ["site_admin"]

    if route_path == "/dashboard":
        return ["site_admin", "institution_admin", "program_admin", "instructor"]

    if route_path == "/audit-clo":
        return ["institution_admin", "program_admin"]

    # Default for authenticated pages
    if auth_info["login_required"]:
        return ["site_admin", "institution_admin", "program_admin", "instructor"]

    return ["public"]


def determine_role_access(
    route_path: str, auth_info: Dict, source_file: str
) -> List[str]:
    """Determine which roles can access this route."""
    # API routes are typically accessible based on permissions
    if route_path.startswith("/api/"):
        return _determine_api_role_access(route_path, auth_info)

    return _determine_page_role_access(route_path, auth_info)


def _extract_app_routes(project_root):
    """Extract routes from app.py."""
    routes = []
    app_py = project_root / "app.py"
    if app_py.exists():
        print(f"Extracting routes from {app_py}")
        app_routes = extract_routes_regex(app_py)
        for route in app_routes:
            route["type"] = "page"
            route["blueprint"] = "app"
            if route.get("function_name"):
                auth_info = extract_auth_requirements(app_py, route["function_name"])
                route.update(auth_info)
        routes.extend(app_routes)
    return routes


def _extract_api_routes(project_root):
    """Extract routes from api_routes.py."""
    routes = []
    api_routes_py = project_root / "api_routes.py"
    if api_routes_py.exists():
        print(f"Extracting routes from {api_routes_py}")
        api_routes_list = extract_routes_regex(api_routes_py)
        for route in api_routes_list:
            route["type"] = "api"
            route["path"] = "/api" + route["path"]
            if route.get("function_name"):
                auth_info = extract_auth_requirements(
                    api_routes_py, route["function_name"]
                )
                route.update(auth_info)
        routes.extend(api_routes_list)
    return routes


def _extract_blueprint_routes(project_root):
    """Extract routes from api/routes/*.py."""
    routes = []
    api_routes_dir = project_root / "api" / "routes"
    if api_routes_dir.exists():
        for route_file in api_routes_dir.glob("*.py"):
            if route_file.name == "__init__.py" or "test" in route_file.name.lower():
                continue
            print(f"Extracting routes from {route_file}")
            blueprint_routes = extract_routes_regex(route_file)
            prefix = get_blueprint_prefix(route_file)
            for route in blueprint_routes:
                route["type"] = "api"
                if prefix and not route["path"].startswith(prefix):
                    route["path"] = prefix + route["path"]
                elif not route["path"].startswith("/api"):
                    route["path"] = "/api" + route["path"]
                if route.get("function_name"):
                    auth_info = extract_auth_requirements(
                        route_file, route["function_name"]
                    )
                    route.update(auth_info)
            routes.extend(blueprint_routes)
    return routes


def _deduplicate_routes(routes):
    """Deduplicate routes by path + methods."""
    seen = set()
    unique_routes = []
    for route in routes:
        key = (route.get("path", ""), tuple(sorted(route.get("methods", []))))
        if key not in seen:
            seen.add(key)
            unique_routes.append(route)
    return unique_routes


def _enrich_routes(unique_routes):
    """Organize and enrich routes with metadata."""
    organized_routes = []
    for route in unique_routes:
        route_path = route.get("path", "")
        auth_info = {
            "login_required": route.get("login_required", False),
            "permission_required": route.get("permission_required"),
            "has_permission_check": route.get("has_permission_check", False),
        }

        template = map_route_to_template(route_path, route.get("source_file", ""))
        role_access = determine_role_access(
            route_path, auth_info, route.get("source_file", "")
        )

        organized_routes.append(
            {
                "path": route_path,
                "methods": route.get("methods", ["GET"]),
                "type": route.get("type", "unknown"),
                "template": template,
                "login_required": auth_info["login_required"],
                "permission_required": auth_info["permission_required"],
                "role_access": role_access,
                "source_file": route.get("source_file", ""),
                "function_name": route.get("function_name", ""),
            }
        )
    return organized_routes


def _write_page_routes_section(f, page_routes):
    """Write page routes table."""
    f.write(f"### Page Routes ({len(page_routes)} total)\n\n")
    f.write("| Path | Methods | Template | Auth Required | Permission | Roles |\n")
    f.write("|------|---------|----------|---------------|------------|-------|\n")

    for route in sorted(page_routes, key=lambda x: x["path"]):
        methods = ", ".join(route["methods"])
        template = route["template"] or "N/A"
        auth = "Yes" if route["login_required"] else "No"
        permission = route["permission_required"] or "-"
        roles = ", ".join(route["role_access"])
        f.write(
            f"| `{route['path']}` | {methods} | `{template}` | {auth} | {permission} | {roles} |\n"
        )


def _write_api_routes_section(f, api_routes):
    """Write API routes table."""
    f.write(f"\n### API Routes ({len(api_routes)} total)\n\n")
    f.write("| Path | Methods | Auth Required | Permission | Roles |\n")
    f.write("|------|---------|---------------|------------|-------|\n")

    for route in sorted(api_routes, key=lambda x: x["path"]):
        methods = ", ".join(route["methods"])
        auth = "Yes" if route["login_required"] else "No"
        permission = route["permission_required"] or "-"
        roles = ", ".join(route["role_access"])
        f.write(
            f"| `{route['path']}` | {methods} | {auth} | {permission} | {roles} |\n"
        )


def _write_role_routes_section(f, organized_routes):
    """Write routes organized by role."""
    f.write("\n## Routes by Role\n\n")

    for role in [
        "public",
        "instructor",
        "program_admin",
        "institution_admin",
        "site_admin",
    ]:
        role_routes = [
            r
            for r in organized_routes
            if role in r["role_access"]
            or (role == "public" and "public" in r["role_access"])
        ]
        if role_routes:
            f.write(f"### {role.replace('_', ' ').title()}\n\n")
            for route in sorted(role_routes, key=lambda x: (x["type"], x["path"])):
                methods = ", ".join(route["methods"])
                f.write(f"- `{route['path']}` ({methods}) - {route['type']}\n")
            f.write("\n")


def _write_markdown_report(output_file, organized_routes):
    """Generate markdown report."""
    page_routes = [r for r in organized_routes if r["type"] == "page"]
    api_routes = [r for r in organized_routes if r["type"] == "api"]

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Route Inventory\n\n")
        f.write(
            "Generated comprehensive inventory of all routes in the application.\n\n"
        )
        f.write("## Route Organization\n\n")

        _write_page_routes_section(f, page_routes)
        _write_api_routes_section(f, api_routes)
        _write_role_routes_section(f, organized_routes)

    print(f"\nRoute inventory generated: {output_file}")
    print(f"Total routes found: {len(organized_routes)}")
    print(f"  - Page routes: {len(page_routes)}")
    print(f"  - API routes: {len(api_routes)}")


def main():
    """Generate route inventory."""
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "logs" / "exploration"
    output_dir.mkdir(parents=True, exist_ok=True)

    routes = []
    routes.extend(_extract_app_routes(project_root))
    routes.extend(_extract_api_routes(project_root))
    routes.extend(_extract_blueprint_routes(project_root))

    unique_routes = _deduplicate_routes(routes)
    organized_routes = _enrich_routes(unique_routes)

    output_file = output_dir / "route_inventory.md"
    _write_markdown_report(output_file, organized_routes)


if __name__ == "__main__":
    main()
