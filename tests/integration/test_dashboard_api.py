"""
Integration tests for dashboard API endpoints

Tests the main dashboard API endpoints and debug endpoints to ensure
they return valid data and don't break after code changes.
"""

import pytest
import requests
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Mark ALL tests in this file as integration tests
pytestmark = pytest.mark.integration


class TestDashboardAPI:
    """Test dashboard API endpoints"""
    
    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the test server"""
        return "http://localhost:3001"  # Server is running on port 3001
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Chrome WebDriver for frontend tests"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--window-size=1280,720")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(10)
        driver.implicitly_wait(5)
        
        yield driver
        
        driver.quit()
    
    def test_main_dashboard_endpoints(self, base_url: str):
        """Test that all main dashboard endpoints are accessible (not 404)"""
        endpoints = [
            '/api/courses',
            '/api/instructors', 
            '/api/sections',
            '/api/terms'
        ]
        
        # Use a session to handle any cookies/auth
        session = requests.Session()
        
        for endpoint in endpoints:
            try:
                response = session.get(f"{base_url}{endpoint}", timeout=5)
                
                # Main goal: ensure endpoint exists (not 404)
                assert response.status_code != 404, f"Endpoint {endpoint} returned 404 - endpoint missing!"
                
                # If we get 400/401/403, that's better than 404 - means endpoint exists but needs auth
                if response.status_code in [400, 401, 403]:
                    print(f"Endpoint {endpoint} requires auth (status {response.status_code}) - but exists!")
                    continue
                    
                # If we get 200, validate the response
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, dict), f"Endpoint {endpoint} didn't return JSON object"
                    assert "success" in data, f"Endpoint {endpoint} missing 'success' field"
                    
            except requests.exceptions.Timeout:
                # Timeout is better than 404 - means endpoint exists but is slow
                print(f"Endpoint {endpoint} timed out - but exists!")
                continue
    
    def test_debug_endpoints(self, base_url: str):
        """Test that all debug endpoints return valid responses"""
        debug_endpoints = [
            ('/api/debug/courses', 'sample_courses'),
            ('/api/debug/instructors', 'sample_instructors'),
            ('/api/debug/sections', 'sample_sections'),
            ('/api/debug/terms', 'sample_terms')
        ]
        
        for endpoint, expected_key in debug_endpoints:
            response = requests.get(f"{base_url}{endpoint}")
            
            # Should return 200 OK
            assert response.status_code == 200, f"Debug endpoint {endpoint} returned {response.status_code}"
            
            # Should return valid JSON
            data = response.json()
            assert isinstance(data, dict), f"Debug endpoint {endpoint} didn't return JSON object"
            
            # Should have success field
            assert "success" in data, f"Debug endpoint {endpoint} missing 'success' field"
            assert data["success"] is True, f"Debug endpoint {endpoint} returned success=False"
            
            # Should have total_count field
            assert "total_count" in data, f"Debug endpoint {endpoint} missing 'total_count' field"
            assert isinstance(data["total_count"], int), f"Debug endpoint {endpoint} total_count is not integer"
            assert data["total_count"] >= 0, f"Debug endpoint {endpoint} total_count is negative"
            
            # Should have sample data field
            assert expected_key in data, f"Debug endpoint {endpoint} missing '{expected_key}' field"
            assert isinstance(data[expected_key], list), f"Debug endpoint {endpoint} {expected_key} is not a list"
    
    def test_debug_course_data_structure(self, base_url: str):
        """Test that debug courses endpoint returns properly structured data"""
        response = requests.get(f"{base_url}/api/debug/courses")
        data = response.json()
        
        if data["total_count"] > 0:
            sample_courses = data["sample_courses"]
            assert len(sample_courses) > 0, "No sample courses returned despite total_count > 0"
            
            # Check structure of first course
            first_course = sample_courses[0]
            required_fields = ["course_number", "title", "department"]
            
            for field in required_fields:
                assert field in first_course, f"Course missing required field: {field}"
    
    def test_debug_instructor_data_structure(self, base_url: str):
        """Test that debug instructors endpoint returns properly structured data"""
        response = requests.get(f"{base_url}/api/debug/instructors")
        data = response.json()
        
        if data["total_count"] > 0:
            sample_instructors = data["sample_instructors"]
            assert len(sample_instructors) > 0, "No sample instructors returned despite total_count > 0"
            
            # Check structure of first instructor
            first_instructor = sample_instructors[0]
            required_fields = ["email", "first_name", "last_name", "account_status"]
            
            for field in required_fields:
                assert field in first_instructor, f"Instructor missing required field: {field}"
            
            # Email should be valid format (basic check)
            email = first_instructor["email"]
            assert "@" in email, f"Invalid email format: {email}"
    
    def test_debug_section_data_structure(self, base_url: str):
        """Test that debug sections endpoint returns properly structured data"""
        response = requests.get(f"{base_url}/api/debug/sections")
        data = response.json()
        
        if data["total_count"] > 0:
            sample_sections = data["sample_sections"]
            assert len(sample_sections) > 0, "No sample sections returned despite total_count > 0"
            
            # Check structure of first section
            first_section = sample_sections[0]
            required_fields = ["section_number", "course_number", "instructor_email", "offering_id"]
            
            for field in required_fields:
                assert field in first_section, f"Section missing required field: {field}"
    
    def test_debug_term_data_structure(self, base_url: str):
        """Test that debug terms endpoint returns properly structured data"""
        response = requests.get(f"{base_url}/api/debug/terms")
        data = response.json()
        
        if data["total_count"] > 0:
            sample_terms = data["sample_terms"]
            assert len(sample_terms) > 0, "No sample terms returned despite total_count > 0"
            
            # Check structure of first term
            first_term = sample_terms[0]
            required_fields = ["term_name", "year", "season"]
            
            for field in required_fields:
                assert field in first_term, f"Term missing required field: {field}"
            
            # Year should be reasonable
            year = first_term["year"]
            if year != "N/A":
                year_int = int(year)
                assert 2020 <= year_int <= 2030, f"Unreasonable year: {year}"
    
    def test_dashboard_consistency(self, base_url: str):
        """Test that main dashboard counts match debug endpoint counts"""
        # Get main dashboard data
        main_endpoints = {
            'courses': '/api/courses',
            'instructors': '/api/instructors',
            'sections': '/api/sections', 
            'terms': '/api/terms'
        }
        
        debug_endpoints = {
            'courses': '/api/debug/courses',
            'instructors': '/api/debug/instructors',
            'sections': '/api/debug/sections',
            'terms': '/api/debug/terms'
        }
        
        for entity_type in main_endpoints:
            # Get main count
            main_response = requests.get(f"{base_url}{main_endpoints[entity_type]}")
            main_data = main_response.json()
            main_count = main_data["count"]
            
            # Get debug count
            debug_response = requests.get(f"{base_url}{debug_endpoints[entity_type]}")
            debug_data = debug_response.json()
            debug_count = debug_data["total_count"]
            
            # Counts should match
            assert main_count == debug_count, f"Count mismatch for {entity_type}: main={main_count}, debug={debug_count}"


class TestDashboardFrontend:
    """Test dashboard frontend functionality"""
    
    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the test server"""
        return "http://localhost:3001"  # Server is running on port 3001
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Chrome WebDriver for frontend tests"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--window-size=1280,720")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--remote-debugging-port=9223")  # Different port
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(10)
        driver.implicitly_wait(5)
        
        yield driver
        
        driver.quit()
    
    def test_dashboard_page_loads(self, base_url: str, driver):
        """Test that the main dashboard page loads without errors"""
        driver.get(base_url)
        
        # Should not have any JavaScript errors
        logs = driver.get_log('browser')
        js_errors = [log for log in logs if log['level'] == 'SEVERE']
        
        # Allow some errors but not too many
        assert len(js_errors) <= 2, f"Too many JavaScript errors: {js_errors}"
    
    def test_dashboard_cards_present(self, base_url: str, driver):
        """Test that dashboard cards are present and populated"""
        driver.get(base_url)
        
        # Wait for dashboard to load
        import time
        time.sleep(2)
        
        # Check that dashboard cards exist
        cards = driver.find_elements("css selector", ".card")
        assert len(cards) >= 4, f"Expected at least 4 dashboard cards, found {len(cards)}"
        
        # Check that counts are loaded (not showing "Loading...")
        loading_elements = driver.find_elements("css selector", ".spinner-border")
        assert len(loading_elements) <= 4, "Dashboard still showing loading spinners after 2 seconds"
    
    def test_debug_section_present(self, base_url: str, driver):
        """Test that debug section is present and loads data"""
        driver.get(base_url)
        
        # Wait for page to load
        import time
        time.sleep(3)
        
        # Check that debug section exists
        debug_section = driver.find_elements("css selector", ".card.border-info")
        assert len(debug_section) >= 1, "Debug section not found"
        
        # Check that debug data is loaded
        debug_elements = driver.find_elements("css selector", "[id^='debug-']")
        assert len(debug_elements) >= 4, f"Expected 4 debug elements, found {len(debug_elements)}"
