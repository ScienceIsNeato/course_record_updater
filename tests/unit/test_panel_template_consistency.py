"""
Test panel template consistency across dashboard HTML templates.

These tests enforce the standard dashboard panel template pattern:
- Every panel MUST have a panel-toggle button
- Every panel with a Manage button MUST link to a valid route
- Add buttons MUST use btn-primary class
- Manage buttons MUST use btn-outline-secondary class
"""

import re
from pathlib import Path

import pytest

# Valid routes that panel buttons can link to
VALID_MANAGE_ROUTES = [
    "/programs",
    "/courses",
    "/terms",
    "/offerings",
    "/faculty",
    "/sections",
    "/audit-clo",
    "/assessments",
]


def find_project_root():
    """Find the project root by looking for known markers."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "templates").exists() and (current / "static").exists():
            return current
        current = current.parent
    return None


class TestPanelTemplateConsistency:
    """Test that dashboard panels follow consistent template patterns."""

    @pytest.fixture
    def templates_dir(self):
        """Get the templates directory path."""
        project_root = find_project_root()
        if not project_root:
            pytest.skip("Could not find project root")
        return project_root / "templates" / "dashboard"

    @pytest.fixture
    def institution_admin_html(self, templates_dir):
        """Load the institution admin template."""
        template_path = templates_dir / "institution_admin.html"
        if template_path.exists():
            return template_path.read_text()
        pytest.skip("institution_admin.html not found")

    @pytest.fixture
    def program_admin_html(self, templates_dir):
        """Load the program admin template."""
        template_path = templates_dir / "program_admin.html"
        if template_path.exists():
            return template_path.read_text()
        pytest.skip("program_admin.html not found")

    @pytest.fixture
    def instructor_html(self, templates_dir):
        """Load the instructor template."""
        template_path = templates_dir / "instructor.html"
        if template_path.exists():
            return template_path.read_text()
        pytest.skip("instructor.html not found")

    def _extract_panels(self, html_content):
        """Extract all dashboard panels from HTML content."""
        # Match dashboard-panel divs and their content
        panel_pattern = r'<div class="dashboard-panel"[^>]*id="([^"]+)"[^>]*>(.*?)</div>\s*</div>\s*</div>'
        panels = re.findall(panel_pattern, html_content, re.DOTALL)
        return panels

    def _extract_panel_buttons(self, html_content):
        """Extract all buttons from panel-actions divs."""
        buttons = []

        # Find all panel-actions blocks
        actions_pattern = (
            r'<div class="panel-actions">(.*?)</div>\s*<button class="panel-toggle"'
        )
        action_blocks = re.findall(actions_pattern, html_content, re.DOTALL)

        for block in action_blocks:
            # Extract individual button elements - match each button tag separately
            button_pattern = (
                r'<button[^>]*class="([^"]*)"[^>]*onclick="([^"]*)"[^>]*>(.*?)</button>'
            )
            found_buttons = re.findall(button_pattern, block, re.DOTALL)
            buttons.extend(found_buttons)

        return buttons

    def _extract_href_from_onclick(self, onclick):
        """Extract the href from window.location.href='...' onclick handlers."""
        match = re.search(r"window\.location\.href='([^']+)'", onclick)
        return match.group(1) if match else None

    def test_institution_admin_panels_have_toggle_buttons(self, institution_admin_html):
        """Verify every panel has a panel-toggle button."""
        # Count panels
        panel_count = institution_admin_html.count('class="dashboard-panel"')
        toggle_count = institution_admin_html.count('class="panel-toggle"')

        assert toggle_count >= panel_count, (
            f"Found {panel_count} panels but only {toggle_count} toggle buttons. "
            "Every panel must have a panel-toggle button."
        )

    def test_institution_admin_manage_buttons_have_valid_routes(
        self, institution_admin_html
    ):
        """Verify all Manage buttons link to valid routes."""
        buttons = self._extract_panel_buttons(institution_admin_html)

        invalid_routes = []
        for btn_class, onclick, label in buttons:
            href = self._extract_href_from_onclick(onclick)
            if href and "Manage" in label:
                if href not in VALID_MANAGE_ROUTES:
                    invalid_routes.append((label.strip(), href))

        assert not invalid_routes, (
            f"Found Manage buttons with invalid routes: {invalid_routes}. "
            f"Valid routes are: {VALID_MANAGE_ROUTES}"
        )

    def test_institution_admin_add_buttons_use_primary_class(
        self, institution_admin_html
    ):
        """Verify Add buttons use btn-primary class."""
        buttons = self._extract_panel_buttons(institution_admin_html)

        wrong_class_buttons = []
        for btn_class, onclick, label in buttons:
            # Clean up label text
            clean_label = re.sub(r"<[^>]+>", "", label).strip()
            if "Add" in clean_label or "Invite" in clean_label:
                if "btn-primary" not in btn_class:
                    wrong_class_buttons.append((clean_label, btn_class))

        assert not wrong_class_buttons, (
            f"Found Add/Invite buttons without btn-primary class: {wrong_class_buttons}. "
            "All Add buttons should use btn-primary."
        )

    def test_institution_admin_manage_buttons_use_outline_secondary_class(
        self, institution_admin_html
    ):
        """Verify Manage buttons use btn-outline-secondary class."""
        buttons = self._extract_panel_buttons(institution_admin_html)

        wrong_class_buttons = []
        for btn_class, onclick, label in buttons:
            # Clean up label text
            clean_label = re.sub(r"<[^>]+>", "", label).strip()
            if "Manage" in clean_label or "Review" in clean_label:
                if "btn-outline-secondary" not in btn_class:
                    wrong_class_buttons.append((clean_label, btn_class))

        assert not wrong_class_buttons, (
            f"Found Manage/Review buttons without btn-outline-secondary class: "
            f"{wrong_class_buttons}. All Manage buttons should use btn-outline-secondary."
        )

    def test_no_dead_links_in_onclick_handlers(self, institution_admin_html):
        """Verify onclick handlers don't link to non-existent pages."""
        # Known invalid routes that don't exist
        invalid_patterns = [
            "/assessment-progress",  # Changed to /offerings
        ]

        for pattern in invalid_patterns:
            assert (
                pattern not in institution_admin_html
            ), f"Found reference to non-existent route: {pattern}"

    def test_program_admin_panels_follow_template(self, program_admin_html):
        """Verify program admin panels follow the template pattern."""
        panel_count = program_admin_html.count('class="dashboard-panel"')
        toggle_count = program_admin_html.count('class="panel-toggle"')

        assert (
            toggle_count >= panel_count
        ), f"Program admin: {panel_count} panels but only {toggle_count} toggle buttons."

    def test_instructor_panels_follow_template(self, instructor_html):
        """Verify instructor panels follow the template pattern."""
        panel_count = instructor_html.count('class="dashboard-panel"')
        toggle_count = instructor_html.count('class="panel-toggle"')

        assert (
            toggle_count >= panel_count
        ), f"Instructor: {panel_count} panels but only {toggle_count} toggle buttons."
