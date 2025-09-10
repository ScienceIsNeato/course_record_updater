"""
Frontend Smoke Tests

These tests verify that the basic UI functionality works without requiring manual interaction.
They catch JavaScript errors, missing elements, and basic functionality issues.
"""

import json
import time

import pytest
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestFrontendSmoke:
    """Smoke tests for frontend functionality"""

    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome driver with headless option"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the application"""
        return "http://localhost:3001"

    def test_server_is_running(self, base_url):
        """Test that the server is accessible"""
        response = requests.get(base_url)
        assert response.status_code == 200
        assert "Course Record Updater" in response.text

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
        time.sleep(2)

        # Check console logs for initialization messages
        logs = driver.get_log("browser")
        log_messages = [log["message"] for log in logs]

        # Look for expected initialization messages
        expected_messages = [
            "script.js loaded",
            "DOM fully loaded and parsed",
            "🔧 Initializing import form...",
            "✅ Adding submit event listener to import form",
        ]

        for expected in expected_messages:
            found = any(expected in msg for msg in log_messages)
            if not found:
                pytest.fail(f"Expected initialization message not found: '{expected}'")

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
        submit_btn = driver.find_element(By.ID, "executeImportBtn")
        submit_btn.click()

        # Check if browser alert appears (JavaScript validation)
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()

            assert "Please select an Excel file" in alert_text
        except TimeoutException:
            pytest.fail("Expected validation alert did not appear")

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

        # Look for dashboard section
        dashboard = driver.find_element(By.CLASS_NAME, "card")
        assert "Course Management Dashboard" in dashboard.text

        # Check for dashboard cards
        expected_cards = ["Courses", "Instructors", "Sections", "Terms"]
        dashboard_text = dashboard.text

        for card in expected_cards:
            assert card in dashboard_text


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
