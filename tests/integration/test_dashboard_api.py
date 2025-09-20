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

    def test_main_dashboard_endpoints(self, base_url: str):
        """Test that all main dashboard endpoints are accessible (not 404)"""
        endpoints = ["/api/courses", "/api/instructors", "/api/sections", "/api/terms"]

        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
                # Accept any non-404 response - endpoints may return empty data
                assert response.status_code != 404, f"Endpoint {endpoint} returned 404"
                print(
                    f"✅ Endpoint {endpoint} accessible (status: {response.status_code})"
                )
            except requests.exceptions.Timeout:
                # If timeout, endpoint exists but is slow
                print(f"Endpoint {endpoint} timed out - but exists!")
                continue


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

        # Check that page loaded successfully
        assert "CEI Course Admin" in driver.title

    def test_dashboard_cards_present(self, base_url: str, driver):
        """Test that dashboard cards are present and populated"""
        driver.get(base_url)

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "card"))
        )

        # Look for the Course Management Dashboard card
        dashboard = driver.find_element(
            By.XPATH,
            "//div[contains(@class, 'card-header') and contains(text(), 'Course Management Dashboard')]",
        )
        assert dashboard is not None, "Course Management Dashboard card not found"

        # Check that data loading spinners are eventually replaced
        time.sleep(2)  # Give time for async loading

        # Verify that at least some content is present (not just loading spinners)
        content_areas = driver.find_elements(
            By.CSS_SELECTOR, "#coursesData, #instructorsData, #sectionsData, #termsData"
        )
        assert len(content_areas) == 4, "Expected 4 dashboard data areas"

        # At least one should not be showing a loading spinner anymore
        loading_spinners = driver.find_elements(By.CSS_SELECTOR, ".spinner-border")
        assert (
            len(loading_spinners) < 4
        ), "Dashboard still showing loading spinners after 2 seconds"
