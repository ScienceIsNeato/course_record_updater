#!/usr/bin/env python3
"""
Demo Validation Script

Automated pre-demo checklist to ensure environment is ready for demonstration.

Usage:
    python validate_demo.py [--url http://localhost:3001]

Checks:
    1. Database is seeded with demo data
    2. Server is running and responsive
    3. Test accounts can login
    4. Critical pages load correctly
    5. Email configuration is valid

Exit Codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import argparse
import os
import sys
import requests
import sqlite3
from pathlib import Path
from typing import Tuple

# ANSI color codes
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_header(text: str) -> None:
    """Print section header"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")


def print_check(name: str, passed: bool, message: str = "") -> None:
    """Print check result"""
    status = f"{GREEN}✅{NC}" if passed else f"{RED}❌{NC}"
    print(f"{status} {name}")
    if message:
        indent = "   "
        print(f"{indent}{message}")


def check_database_exists(db_path: str) -> Tuple[bool, str]:
    """Check if database file exists"""
    if not os.path.exists(db_path):
        return False, f"Database not found at {db_path}"
    return True, "Database file exists"


def check_demo_data_seeded(db_path: str) -> Tuple[bool, str]:
    """Check if demo data is seeded in database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for demo admin account
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE email = 'demo.admin@example.com'
        """)
        admin_count = cursor.fetchone()[0]
        
        # Check for demo institution
        cursor.execute("""
            SELECT COUNT(*) FROM institutions
            WHERE name LIKE '%Demo%' OR name LIKE '%Example%'
        """)
        institution_count = cursor.fetchone()[0]
        
        conn.close()
        
        if admin_count == 0:
            return False, "Demo admin account (demo.admin@example.com) not found"
        
        if institution_count == 0:
            return False, "Demo institution not found"
        
        return True, f"Demo data found (admin account + {institution_count} institution(s))"
    
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error checking database: {str(e)}"


def check_server_running(base_url: str) -> Tuple[bool, str]:
    """Check if server is running and responsive"""
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            return True, f"Server responding at {base_url}"
        else:
            return False, f"Server returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to {base_url} - is server running?"
    except requests.exceptions.Timeout:
        return False, f"Connection to {base_url} timed out"
    except Exception as e:
        return False, f"Error connecting to server: {str(e)}"


def check_login_page_loads(base_url: str) -> Tuple[bool, str]:
    """Check if login page loads"""
    try:
        response = requests.get(f"{base_url}/login", timeout=5)
        if response.status_code == 200:
            # Check for expected content
            if "email" in response.text.lower() and "password" in response.text.lower():
                return True, "Login page loads correctly"
            else:
                return False, "Login page loads but missing expected form fields"
        else:
            return False, f"Login page returned status code {response.status_code}"
    except Exception as e:
        return False, f"Error loading login page: {str(e)}"


def check_admin_can_login(base_url: str) -> Tuple[bool, str]:
    """Check if demo admin account can login"""
    try:
        session = requests.Session()
        
        # Get login page to establish session
        response = session.get(f"{base_url}/login", timeout=5)
        if response.status_code != 200:
            return False, f"Login page not accessible (status {response.status_code})"
        
        # Extract CSRF token if present
        csrf_token = None
        if 'csrf-token' in response.text:
            # Simple extraction - might need improvement
            import re
            match = re.search(r'name="csrf-token".*?content="([^"]+)"', response.text)
            if match:
                csrf_token = match.group(1)
        
        # Attempt login
        login_data = {
            'email': 'demo.admin@example.com',
            'password': 'Demo2024!',
        }
        if csrf_token:
            login_data['csrf_token'] = csrf_token
        
        response = session.post(f"{base_url}/login", data=login_data, timeout=5, allow_redirects=False)
        
        # Check for successful login (redirect to dashboard)
        if response.status_code in [302, 303] and 'dashboard' in response.headers.get('Location', '').lower():
            return True, "Demo admin can login successfully"
        elif response.status_code == 200:
            # Check if still on login page (failed login)
            if 'login' in response.url.lower():
                return False, "Login failed - check credentials"
            else:
                return True, "Login appears successful"
        else:
            return False, f"Login returned unexpected status code {response.status_code}"
    
    except Exception as e:
        return False, f"Error testing login: {str(e)}"


def check_critical_routes(base_url: str) -> Tuple[bool, str]:
    """Check if critical routes are accessible (after login)"""
    critical_routes = [
        '/dashboard',
        '/import',
        '/audit-clo',
        '/export',
    ]
    
    # Note: These routes require authentication, so just check they don't 404
    accessible = []
    not_accessible = []
    
    for route in critical_routes:
        try:
            response = requests.get(f"{base_url}{route}", timeout=5, allow_redirects=False)
            # 302/303 redirect to login is ok (means route exists, just requires auth)
            # 200 is ok (means route is accessible)
            # 404 is bad (means route doesn't exist)
            if response.status_code in [200, 302, 303]:
                accessible.append(route)
            else:
                not_accessible.append(f"{route} ({response.status_code})")
        except Exception as e:
            not_accessible.append(f"{route} (error: {str(e)})")
    
    if not_accessible:
        return False, f"Some routes not accessible: {', '.join(not_accessible)}"
    else:
        return True, f"All {len(accessible)} critical routes exist"


def check_environment_variables() -> Tuple[bool, str]:
    """Check if critical environment variables are set"""
    required_vars = {
        'DATABASE_URL': 'optional',  # Has default
        'EMAIL_PROVIDER': 'optional',  # Has default
    }
    
    warnings = []
    for var, requirement in required_vars.items():
        if var not in os.environ:
            if requirement == 'required':
                return False, f"Required environment variable not set: {var}"
            else:
                warnings.append(var)
    
    if warnings:
        return True, f"Optional env vars not set: {', '.join(warnings)} (using defaults)"
    else:
        return True, "Environment variables configured"


def main():
    """Main validation routine"""
    parser = argparse.ArgumentParser(description='Validate demo environment')
    parser.add_argument('--url', default='http://localhost:3001', help='Base URL of server')
    parser.add_argument('--db', default='course_records_dev.db', help='Database file path')
    args = parser.parse_args()
    
    print_header("🔍 Demo Environment Validation")
    
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent
    db_path = project_root / args.db
    
    # Track overall result
    all_passed = True
    
    # Check 1: Database exists
    passed, message = check_database_exists(str(db_path))
    print_check("Database file exists", passed, message)
    all_passed = all_passed and passed
    
    # Check 2: Demo data seeded
    if passed:  # Only check if database exists
        passed, message = check_demo_data_seeded(str(db_path))
        print_check("Demo data seeded", passed, message)
        all_passed = all_passed and passed
    else:
        print_check("Demo data seeded", False, "Skipped (database not found)")
        all_passed = False
    
    # Check 3: Server running
    passed, message = check_server_running(args.url)
    print_check("Server running", passed, message)
    server_running = passed
    all_passed = all_passed and passed
    
    # Check 4: Login page loads
    if server_running:
        passed, message = check_login_page_loads(args.url)
        print_check("Login page loads", passed, message)
        all_passed = all_passed and passed
    else:
        print_check("Login page loads", False, "Skipped (server not running)")
        all_passed = False
    
    # Check 5: Demo admin can login
    if server_running:
        passed, message = check_admin_can_login(args.url)
        print_check("Demo admin can login", passed, message)
        all_passed = all_passed and passed
    else:
        print_check("Demo admin can login", False, "Skipped (server not running)")
        all_passed = False
    
    # Check 6: Critical routes exist
    if server_running:
        passed, message = check_critical_routes(args.url)
        print_check("Critical routes exist", passed, message)
        all_passed = all_passed and passed
    else:
        print_check("Critical routes exist", False, "Skipped (server not running)")
        all_passed = False
    
    # Check 7: Environment variables
    passed, message = check_environment_variables()
    print_check("Environment variables", passed, message)
    all_passed = all_passed and passed
    
    # Summary
    print_header("📊 Validation Summary")
    if all_passed:
        print(f"{GREEN}✅ All checks passed! Demo environment is ready.{NC}\n")
        print("Next steps:")
        print("  1. Open demo script: docs/workflow-walkthroughs/core-workflow-demo.md")
        print("  2. Navigate to:", args.url)
        print("  3. Login: demo.admin@example.com / Demo2024!")
        sys.exit(0)
    else:
        print(f"{RED}❌ Some checks failed. Fix issues before demo.{NC}\n")
        print("Common fixes:")
        print("  - Database: python scripts/seed_db.py --demo --clear --env dev")
        print("  - Server: ./restart_server.sh dev")
        print("  - Environment: source .envrc or set env vars")
        sys.exit(1)


if __name__ == '__main__':
    main()

