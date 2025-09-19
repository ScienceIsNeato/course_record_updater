"""
Integration tests for dashboard API endpoints

Clean greenfield tests focusing on core functionality without legacy debug cruft.
"""

import time

import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestDashboardAPI:
    """Test dashboard API functionality"""

    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the application"""
        import os

        port = os.environ.get("COURSE_RECORD_UPDATER_PORT", "3001")
        return f"http://localhost:{port}"

    def test_dashboard_data_endpoint(self, base_url: str):
        """Ensure the aggregated dashboard endpoint is reachable."""
        endpoint = f"{base_url}/api/dashboard/data"

        try:
            response = requests.get(
                endpoint,
                timeout=10,
                headers={"Accept": "application/json"},
            )
        except requests.exceptions.ConnectionError as exc:
            pytest.skip(f"Dashboard server unavailable: {exc}")
        except requests.exceptions.Timeout:
            pytest.skip("Dashboard server timed out while fetching data")

        # Without authentication we should receive a 401 JSON response
        if response.status_code == 401:
            payload = response.json()
            assert payload.get("error_code") == "AUTH_REQUIRED"
        else:
            assert response.status_code != 404, "Dashboard endpoint returned 404"
            assert response.ok, f"Unexpected status code: {response.status_code}"


class TestDashboardFrontend:
    """Test dashboard frontend functionality"""

    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the application"""
        import os

        port = os.environ.get("COURSE_RECORD_UPDATER_PORT", "3001")
        return f"http://localhost:{port}"

    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome driver with headless option"""
        import os

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument("--headless")  # Run in headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Check for Chrome in common macOS locations
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chrome.app/Contents/MacOS/Chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
        ]

        chrome_path = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_path = path
                break

        if chrome_path:
            options.binary_location = chrome_path

        driver = webdriver.Chrome(options=options)
        yield driver
        driver.quit()

    def test_dashboard_page_loads(self, base_url: str, driver):
        """Test that the main dashboard page loads without errors"""
        driver.get(base_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check if we're on login page (authentication required) or main page
        page_source = driver.page_source
        if "Welcome Back" in page_source:
            # On login page - this is expected with authentication enabled
            assert "loginForm" in page_source or "email" in page_source
        else:
            # On main page - check for expected content
            assert "CEI Course Admin" in page_source

        # Check that page loaded successfully (title varies based on page)
        title = driver.title
        assert title is not None and len(title) > 0

    def test_dashboard_cards_present(self, base_url: str, driver):
        """Test that dashboard cards are present and populated"""
        driver.get(base_url)

        # Skip this test if we're on the login page
        if "Welcome Back" in driver.page_source:
            pytest.skip("Test requires authenticated access to main page")

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "card"))
        )

        # Look for the panel-based dashboard layout
        panels = driver.find_elements(By.CSS_SELECTOR, ".dashboard-panel")
        assert panels, "Expected at least one dashboard panel"

        # Ensure panel titles rendered
        panel_titles = driver.find_elements(
            By.CSS_SELECTOR, ".dashboard-panel .panel-title"
        )
        assert panel_titles, "Dashboard panel titles not found"

        # Give async data fetch a moment to populate panels
        time.sleep(2)

        # Verify that at least one panel replaced its loading placeholder
        panel_contents = driver.find_elements(
            By.CSS_SELECTOR, ".dashboard-panel .panel-content"
        )
        assert panel_contents, "Dashboard panel content areas missing"
        fully_loaded = [
            content
            for content in panel_contents
            if "panel-loading" not in content.get_attribute("innerHTML")
        ]
        assert (
            fully_loaded
        ), "Dashboard panels still show only loading placeholders after wait"
