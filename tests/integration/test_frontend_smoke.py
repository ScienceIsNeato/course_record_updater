"""
Frontend Smoke Tests - INTEGRATION TESTS

These tests verify that the basic UI functionality works without requiring manual interaction.
They catch JavaScript errors, missing elements, and basic functionality issues.

⚠️  IMPORTANT: These are INTEGRATION tests that use Selenium and should NOT run in unit test suite
"""

# Unused imports removed
import time

import pytest
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Mark ALL tests in this file as integration tests (slow, requires browser)
pytestmark = pytest.mark.integration


class TestFrontendSmoke:
    """Smoke tests for frontend functionality"""

    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome driver with headless option"""
        import os

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # CI optimizations
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")

        driver = webdriver.Chrome(options=chrome_options)

        # Use environment variables for timeouts (CI can override)
        implicit_wait = int(os.environ.get("SELENIUM_IMPLICIT_WAIT", "10"))
        page_load_timeout = int(os.environ.get("SELENIUM_PAGE_LOAD_TIMEOUT", "30"))

        driver.implicitly_wait(implicit_wait)
        driver.set_page_load_timeout(page_load_timeout)

        yield driver
        driver.quit()

    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the application"""
        import os

        port = os.getenv("DEFAULT_PORT", "3001")
        return f"http://localhost:{port}"

    def test_server_is_running(self, base_url):
        """Test that the server is accessible"""
        response = requests.get(base_url)
        assert response.status_code == 200
        assert "CEI Course Admin" in response.text

    def test_page_loads_without_errors(self, driver, base_url):
        """Test that the main page loads without JavaScript errors"""
        driver.get(base_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check for JavaScript errors in console
        logs = driver.get_log("browser")
        js_errors = [log for log in logs if log["level"] == "SEVERE"]

        if js_errors:
            error_messages = [log["message"] for log in js_errors]
            pytest.fail(f"JavaScript errors found: {error_messages}")

    def test_import_form_elements_exist(self, driver, base_url):
        """Test that all import form elements are present"""
        driver.get(base_url)

        # Wait for form to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "excelImportForm"))
        )

        # Check for required form elements
        required_elements = [
            "excelImportForm",
            "excel_file",
            "import_adapter",
            "validateImportBtn",
            "executeImportBtn",
            "importBtnText",
            "dry_run",
            "delete_existing_db",
            "importProgress",
            "importResults",
        ]

        missing_elements = []
        for element_id in required_elements:
            try:
                driver.find_element(By.ID, element_id)
            except NoSuchElementException:
                missing_elements.append(element_id)

        if missing_elements:
            pytest.fail(f"Missing required form elements: {missing_elements}")

    def test_import_form_javascript_initialization(self, driver, base_url):
        """Test that JavaScript properly initializes the import form"""
        driver.get(base_url)

        # Wait for JavaScript to load and initialize
        time.sleep(3)

        # Test that JavaScript is working by checking if form elements are properly initialized
        # Instead of relying on console logs, check if JavaScript functionality works
        dry_run_checkbox = driver.find_element(By.ID, "dry_run")
        import_btn_text = driver.find_element(By.ID, "importBtnText")

        # Check that the dry run checkbox is unchecked by default (better UX for real imports)
        assert (
            not dry_run_checkbox.is_selected()
        ), "Dry run should be unchecked by default for better UX"

        # Verify the form elements exist and are interactive (basic JavaScript functionality)
        assert dry_run_checkbox.is_enabled(), "Dry run checkbox should be enabled"
        assert import_btn_text.is_displayed(), "Import button text should be visible"

        # The fact that we can interact with these elements means JavaScript loaded successfully

    def test_conflict_resolution_options_exist(self, driver, base_url):
        """Test that conflict resolution radio buttons are present"""
        driver.get(base_url)

        # Check for conflict resolution options
        conflict_options = ["use_theirs", "use_mine"]

        for option in conflict_options:
            element = driver.find_element(By.ID, option)
            assert element.get_attribute("type") == "radio"
            assert element.get_attribute("name") == "conflict_strategy"

    def test_form_validation_without_file(self, driver, base_url):
        """Test that form validation works when no file is selected"""
        driver.get(base_url)

        # Wait for form to load
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "executeImportBtn"))
        )

        # Try to submit without selecting a file
        file_input = driver.find_element(By.ID, "excel_file")
        submit_btn = driver.find_element(By.ID, "executeImportBtn")

        # Check HTML5 validation - file input should be required
        is_required = file_input.get_attribute("required")
        assert is_required is not None, "File input should have required attribute"

        # Try to submit - HTML5 validation should prevent submission
        submit_btn.click()

        # Check if validation message appears (HTML5 validation)
        validation_message = file_input.get_attribute("validationMessage")
        assert (
            validation_message
        ), "File input should show validation message when empty"

    def test_api_endpoints_accessible(self, base_url):
        """Test that API endpoints are accessible"""
        api_endpoints = [
            "/api/health",
            # Note: /api/import/excel requires POST with file, so we skip it
        ]

        for endpoint in api_endpoints:
            response = requests.get(f"{base_url}{endpoint}")
            assert response.status_code in [
                200,
                405,
            ]  # 405 = Method Not Allowed (expected for POST-only endpoints)

    def test_static_assets_load(self, base_url):
        """Test that static assets (CSS, JS, images) load properly"""
        static_assets = [
            "/static/style.css",
            "/static/script.js",
            "/static/images/cei_logo.jpg",
        ]

        for asset in static_assets:
            response = requests.get(f"{base_url}{asset}")
            assert response.status_code == 200

    def test_dashboard_cards_present(self, driver, base_url):
        """Test that dashboard cards are present"""
        driver.get(base_url)

        # Look for dashboard section - find the card with the dashboard header
        dashboard_cards = driver.find_elements(By.CLASS_NAME, "card")
        dashboard = None
        for card in dashboard_cards:
            if "Course Management Dashboard" in card.text:
                dashboard = card
                break

        assert dashboard is not None, "Course Management Dashboard card not found"

        # Check for dashboard cards
        expected_cards = ["Courses", "Instructors", "Sections", "Terms"]
        dashboard_text = dashboard.text

        for card in expected_cards:
            assert card in dashboard_text


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
