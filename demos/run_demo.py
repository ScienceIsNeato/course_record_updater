#!/usr/bin/env python3
"""
Interactive Demo Runner

Parses a JSON demo file and provides interactive step-by-step guidance.

Usage:
    python run_demo.py --demo full_semester_workflow.json
    python run_demo.py --demo full_semester_workflow.json --auto
    python run_demo.py --demo full_semester_workflow.json --auto --start-step 5 --fail-fast

Features:
    - Dual execution modes (human-guided and automated)
    - Pre/post command execution with verification
    - Clickable URLs for navigation
    - Screenshot and artifact collection
    - Fast iteration with --start-step and --fail-fast
"""

import argparse
import json
import os
import shlex
import subprocess  # nosec B404
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)

# ANSI color codes
BLUE = '\033[0;34m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
RED = '\033[0;31m'
BOLD = '\033[1m'
NC = '\033[0m'  # No Color

class DemoRunner:
    def __init__(self, demo_file: Path, auto_mode: bool = False, start_step: int = 1,
                 fail_fast: bool = False, verify_only: bool = False):
        self.demo_file = demo_file
        self.auto_mode = auto_mode
        self.start_step = start_step
        self.fail_fast = fail_fast
        self.verify_only = verify_only
        self.demo_data = None
        self.artifact_dir = None
        self.context_vars = {}  # For variable substitution like {{course_id}}
        self.session = requests.Session()  # For maintaining auth cookies
        self.csrf_token = None  # CSRF token for API calls
        self.errors = []  # Track all errors encountered during demo
        self.working_dir: Path = Path(os.getcwd())
        self.manifest_path: Optional[Path] = None
        
    def load_demo(self) -> bool:
        """Load and parse the demo JSON file."""
        try:
            with open(self.demo_file, 'r') as f:
                self.demo_data = json.load(f)
            return True
        except FileNotFoundError:
            self.print_error(f"Demo file not found: {self.demo_file}")
            return False
        except json.JSONDecodeError as e:
            self.print_error(f"Invalid JSON in demo file: {e}")
            return False
    
    def setup_artifacts(self):
        """Create artifact directory for this demo run."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        demo_id = self.demo_data.get('demo_id', 'demo')
        self.artifact_dir = Path(__file__).parent / "artifacts" / f"{demo_id}_{timestamp}"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.artifact_dir / "screenshots").mkdir(exist_ok=True)
        (self.artifact_dir / "logs").mkdir(exist_ok=True)
        (self.artifact_dir / "exports").mkdir(exist_ok=True)
        
        self.print_info(f"Artifacts will be saved to: {self.artifact_dir}")
    
    def validate_environment(self) -> None:
        """Ensure working directory and manifest referenced by demo exist."""
        env_config = self.demo_data.get('environment', {})
        working_directory = env_config.get('working_directory')

        if working_directory:
            candidate = Path(working_directory)
            if not candidate.is_absolute():
                # Resolve relative to CWD (where the script is invoked from)
                # NOT relative to the demo file location
                candidate = (Path.cwd() / candidate).resolve()
            # If it's already absolute, use as-is
        else:
            # Default to CWD
            candidate = Path.cwd()

        if not candidate.exists():
            self.print_error(f"Configured working directory does not exist: {candidate}")
            sys.exit(1)

        self.working_dir = candidate

        setup_commands = env_config.get('setup_commands', [])
        self.manifest_path = self._extract_manifest_path(setup_commands)

        if self.manifest_path is None:
            self.print_error("Demo setup commands must include --manifest <path> for seeding")
            sys.exit(1)

        if not self.manifest_path.exists():
            self.print_error(f"Manifest file not found: {self.manifest_path}")
            sys.exit(1)

        if not any("scripts/seed_db.py" in cmd for cmd in setup_commands):
            self.print_error("Setup commands must include scripts/seed_db.py invocation")
            sys.exit(1)

        if not any("--demo" in cmd for cmd in setup_commands if "scripts/seed_db.py" in cmd):
            self.print_error("Demo seeding command must include --demo flag")
            sys.exit(1)

    def _extract_manifest_path(self, setup_commands: List[str]) -> Optional[Path]:
        """Extract manifest path from setup commands (handles --manifest=path and --manifest path)."""
        for cmd in setup_commands:
            try:
                parts = shlex.split(cmd)
            except ValueError:
                continue

            for index, part in enumerate(parts):
                # Handle --manifest=path format
                if part.startswith('--manifest='):
                    manifest_path = part.split('=', 1)[1]
                    manifest_candidate = Path(manifest_path)
                    if not manifest_candidate.is_absolute():
                        manifest_candidate = (self.working_dir / manifest_candidate).resolve()
                    return manifest_candidate
                # Handle --manifest path format
                if part == '--manifest' and index + 1 < len(parts):
                    manifest_candidate = Path(parts[index + 1])
                    if not manifest_candidate.is_absolute():
                        manifest_candidate = (self.working_dir / manifest_candidate).resolve()
                    return manifest_candidate

        return None

    def run_setup(self) -> bool:
        """Run environment setup commands."""
        env_config = self.demo_data.get('environment', {})
        setup_commands = env_config.get('setup_commands', [])

        if not setup_commands:
            return True

        self.print_header("Environment Setup")
        print(f"Working Directory: {CYAN}{self.working_dir}{NC}\n")
        print("The following commands will prepare the demo environment:\n")

        for i, cmd in enumerate(setup_commands, 1):
            print(f"  {i}. {CYAN}{cmd}{NC}")
        
        if self.verify_only:
            print(f"{YELLOW}[VERIFY-ONLY MODE] Skipping setup execution{NC}\n")
            return True
        
        # Change to working directory for setup
        original_dir = os.getcwd()
        try:
            os.chdir(self.working_dir)
            print()
            for cmd in setup_commands:
                if not self.run_command(cmd, label="Setup"):
                    return False
            
            self.print_success("Setup complete!")
            return True
        finally:
            os.chdir(original_dir)
    
    def run_demo(self):
        """Main demo execution loop."""
        if not self.load_demo():
            sys.exit(1)

        self.validate_environment()

        if not self.verify_only:
            self.setup_artifacts()
        
        # Print demo info
        self.print_header(f"Demo: {self.demo_data.get('demo_name', 'Unnamed Demo')}")
        print(f"Description: {self.demo_data.get('description', 'No description')}")
        print(f"Estimated Duration: {self.demo_data.get('estimated_duration_minutes', '?')} minutes")
        if self.auto_mode:
            print(f"{CYAN}Mode: AUTOMATED{NC}")
        else:
            print(f"{CYAN}Mode: HUMAN-GUIDED{NC}")
        
        if self.start_step > 1:
            print(f"{YELLOW}Starting from step {self.start_step} (skipping steps 1-{self.start_step-1}){NC}")
        
        print()
        
        # Run setup unless starting mid-demo
        if self.start_step == 1:
            if not self.run_setup():
                self.print_error("Setup failed. Exiting.")
                sys.exit(1)
        
        # Run through steps
        steps = self.demo_data.get('steps', [])
        total_steps = len(steps)
        
        for step in steps:
            step_num = step.get('step_number', 0)
            
            # Skip steps before start_step
            if step_num < self.start_step:
                continue
            
            if not self.run_step(step, total_steps):
                if self.fail_fast:
                    self.print_error(f"Demo stopped at step {step_num} due to failure (--fail-fast enabled)")
                    sys.exit(1)
                else:
                    if not self.auto_mode:
                        response = input(f"{YELLOW}Step failed. Continue to next step? (y/n): {NC}").strip().lower()
                        if response != 'y':
                            sys.exit(1)
        
        # Demo complete
        self.print_header("Demo Complete!")
        
        # Show error summary if any errors occurred
        if self.errors:
            print(f"{RED}{BOLD}❌ Error Summary:{NC}")
            print(f"{RED}The following errors occurred during the demo:{NC}\n")
            for i, error in enumerate(self.errors, 1):
                print(f"{RED}  {i}. {error}{NC}")
            print()
        else:
            print(f"{GREEN}✅ All steps completed successfully!{NC}\n")
        
        # Show talking points
        talking_points = self.demo_data.get('talking_points', [])
        if talking_points:
            print("Key Takeaways:")
            for point in talking_points:
                print(f"  • {point}")
            print()
        
        if not self.verify_only:
            print(f"Artifacts saved to: {self.artifact_dir}\n")
    
    def run_step(self, step: Dict, total_steps: int) -> bool:
        """Execute a single demo step."""
        step_num = step.get('step_number', 0)
        phase = step.get('phase', '')
        name = step.get('name', 'Unnamed Step')
        purpose = step.get('purpose', '')
        
        self.current_step = step_num  # Track for error reporting
        
        self.print_step(step_num, total_steps, phase, name)
        print(f"{CYAN}📋 Purpose:{NC} {purpose}\n")
        
        # Run pre-commands
        if not self.run_pre_commands(step.get('pre_commands', [])):
            return False
        
        # Show instructions and handle UI interaction
        if not self.handle_instructions(step):
            return False
        
        # Run post-commands
        if not self.run_post_commands(step.get('post_commands', [])):
            return False
        
        # Collect artifacts
        self.collect_artifacts(step.get('artifacts', {}), step_num)
        
        # Pause for human if needed
        if not self.auto_mode and step.get('pause_for_human', True) and not self.verify_only:
            input(f"\n{GREEN}Press Enter to continue to next step...{NC}\n")
        
        return True
    
    def run_pre_commands(self, commands: List[Dict]) -> bool:
        """Execute pre-step commands."""
        if not commands:
            return True
        
        print(f"{CYAN}🔧 Pre-Step Commands:{NC}")
        for cmd_spec in commands:
            cmd = self._substitute_variables(cmd_spec.get('command', ''))
            purpose = cmd_spec.get('purpose', '')
            expected = cmd_spec.get('expected_output', '')
            expected_contains = cmd_spec.get('expected_output_contains', '')
            capture_as = cmd_spec.get('capture_output_as', '') or cmd_spec.get('capture_as', '')  # Support both keys
            
            print(f"  ✓ {purpose}...")
            print(f"    $ {CYAN}{cmd}{NC}")
            
            if self.verify_only:
                print(f"    {YELLOW}[VERIFY-ONLY MODE] Skipping execution{NC}")
                continue
            
            result = self.run_command_with_capture(cmd)
            if result is None:
                error_msg = f"Step {self.current_step}: Pre-command failed: {cmd}"
                self.errors.append(error_msg)
                self.print_error(f"Command failed: {cmd}")
                if self.fail_fast:
                    return False
                continue
            
            output = result.strip()
            print(f"    Result: {output[:100]}..." if len(output) > 100 else f"    Result: {output}")
            
            # Capture variable if requested
            if capture_as:
                self.context_vars[capture_as] = output
                print(f"    {GREEN}(Captured as {{{{{capture_as}}}}}){NC}")
            
            # Verify output
            if expected and output != expected:
                error_msg = f"Step {self.current_step}: Pre-command verification failed - Expected '{expected}', got '{output[:50]}...'"
                self.errors.append(error_msg)
                self.print_error(f"Expected: {expected}, Got: {output}")
                if self.fail_fast:
                    return False
            elif expected_contains and expected_contains not in output:
                error_msg = f"Step {self.current_step}: Pre-command verification failed - Expected output to contain '{expected_contains}'"
                self.errors.append(error_msg)
                self.print_error(f"Expected output to contain: {expected_contains}")
                if self.fail_fast:
                    return False
            else:
                print(f"    {GREEN}✅ PASS{NC}")
        
        print()
        return True
    
    def run_post_commands(self, commands: List[Dict]) -> bool:
        """Execute post-step verification commands."""
        if not commands:
            return True
        
        print(f"{CYAN}🔍 Post-Step Verification:{NC}")
        for cmd_spec in commands:
            cmd = self._substitute_variables(cmd_spec.get('command', ''))
            purpose = cmd_spec.get('purpose', '')
            expected = cmd_spec.get('expected_output', '')
            expected_contains = cmd_spec.get('expected_output_contains', '')
            capture_as = cmd_spec.get('capture_output_as', '') or cmd_spec.get('capture_as', '')
            
            print(f"  ✓ {purpose}...")
            print(f"    $ {CYAN}{cmd}{NC}")
            
            if self.verify_only:
                print(f"    {YELLOW}[VERIFY-ONLY MODE] Skipping execution{NC}")
                continue
            
            result = self.run_command_with_capture(cmd)
            if result is None:
                error_msg = f"Step {self.current_step}: Verification command failed: {cmd}"
                self.errors.append(error_msg)
                self.print_error(f"Verification command failed: {cmd}")
                if self.fail_fast:
                    return False
                continue
            
            output = result.strip()
            
            # Store captured output as context variable if requested
            if capture_as:
                self.context_vars[capture_as] = output
                print(f"    📝 Captured as {{{{capture_as}}}}")
            
            # Check expectations
            if expected:
                print(f"    Expected: {expected}")
                print(f"    Actual: {output}")
                if output == expected:
                    print(f"    {GREEN}✅ PASS{NC}")
                else:
                    error_msg = f"Step {self.current_step}: Verification failed - Expected '{expected}', got '{output[:50]}...'"
                    self.errors.append(error_msg)
                    print(f"    {RED}✗ FAIL{NC}")
                    if self.fail_fast:
                        return False
            elif expected_contains:
                print(f"    Expected to contain: {expected_contains}")
                print(f"    Actual: {output}")
                if expected_contains in output:
                    print(f"    {GREEN}✅ PASS{NC}")
                else:
                    error_msg = f"Step {self.current_step}: Verification failed - Expected output to contain '{expected_contains}'"
                    self.errors.append(error_msg)
                    print(f"    {RED}✗ FAIL{NC}")
                    if self.fail_fast:
                        return False
            else:
                print(f"    Result: {output}")
                print(f"    {GREEN}✅ PASS{NC}")
        
        print()
        return True
    
    def show_manual_steps(self, action: str, automated: Dict, human_text: str):
        """Show the manual UI steps equivalent to the automated action."""
        print(f"{CYAN}📋 Equivalent Manual Execution Steps:{NC}")
        
        if action == 'api_post' and '/auth/login' in automated.get('endpoint', ''):
            email = automated.get('data', {}).get('email', '')
            password = automated.get('data', {}).get('password', '')
            print(f"  1. Navigate to http://localhost:3001/login")
            print(f"  2. Enter email: {email}")
            print(f"  3. Enter password: {password}")
            print(f"  4. Click 'Login' button")
        elif action == 'api_post' and '/auth/logout' in automated.get('endpoint', ''):
            print(f"  1. Click user dropdown in header")
            print(f"  2. Click 'Logout'")
        elif action == 'api_put' and '/programs/' in automated.get('endpoint', ''):
            desc = automated.get('data', {}).get('description', '')
            print(f"  1. Navigate to Programs page")
            print(f"  2. Find 'Biological Sciences' in table")
            print(f"  3. Click Edit button (pencil icon)")
            print(f"  4. Change description to: \"{desc}\"")
            print(f"  5. Click Save")
        elif action == 'api_post' and '/duplicate' in automated.get('endpoint', ''):
            new_number = automated.get('data', {}).get('new_course_number', '')
            print(f"  1. Navigate to Courses page")
            print(f"  2. Find BIOL-101 in table")
            print(f"  3. Click Duplicate button (copy icon)")
            print(f"  4. Change course number to: {new_number}")
            print(f"  5. Select programs in dropdown")
            print(f"  6. Click 'Duplicate' button")
        elif action == 'api_put' and '/sections/' in automated.get('endpoint', ''):
            data = automated.get('data', {})
            print(f"  1. Navigate to Assessments page")
            print(f"  2. Select course from dropdown")
            print(f"  3. Fill in Students Passed: {data.get('students_passed', '')}")  # nosec B608
            print(f"  4. Fill in Students D/F/IC: {data.get('students_dfic', '')}")
            print(f"  5. Fill in narrative: \"{data.get('narrative_celebrations', '')[:50]}...\"")
            print(f"  6. Click 'Save Course Data'")
        elif action == 'run_command':
            cmd = automated.get('command', '')
            print(f"  This is a background script, no manual UI equivalent")
            print(f"  Script: {cmd}")
        elif human_text:
            # Fall back to human instructions if available
            for line in human_text.split('\n')[:3]:  # Show first 3 lines
                if line.strip():
                    print(f"  {line.strip()}")
        else:
            print(f"  [No manual steps needed - navigation only]")
        print()
    
    def handle_instructions(self, step: Dict) -> bool:
        """Handle step instructions (human or automated)."""
        instructions = step.get('instructions', {})
        urls = step.get('urls', [])
        inputs = step.get('inputs', {})
        expected_results = step.get('expected_results', [])
        
        automated = instructions.get('automated', {})
        action = automated.get('action', '')
        
        # Always show manual steps (for reference and documentation)
        if action and action != 'none':
            self.show_manual_steps(action, automated, instructions.get('human', ''))
        
        if self.auto_mode:
            # Automated mode: execute automated action
            if action and action != 'none':
                print(f"{CYAN}🤖 Automated Action:{NC} {action}")
                if self.verify_only:
                    print(f"{YELLOW}[VERIFY-ONLY MODE] Skipping automation{NC}\n")
                else:
                    # Execute browser automation
                    if not self.execute_browser_action(action, automated):
                        if self.fail_fast:
                            return False
        else:
            # Human mode: show clickable URLs
            if urls:
                print(f"{CYAN}🔗 Quick Links:{NC}")
                for url_spec in urls:
                    label = url_spec.get('label', 'Link')
                    url = url_spec.get('url', '')
                    print(f"  → {label}: {BLUE}{url}{NC}")
                print()
            
            # Show inputs
            if inputs:
                print(f"{CYAN}📝 Inputs for this step:{NC}")
                for key, value in inputs.items():
                    print(f"  • {key}: {value}")
                print()
        
        # Show expected results
        if expected_results:
            print(f"{CYAN}✅ Expected Results:{NC}")
            for result in expected_results:
                print(f"  • {result}")
            print()
        
        return True
    
    def _substitute_variables(self, text: str) -> str:
        """Replace {{variable}} placeholders with context values."""
        import re
        pattern = r'\{\{(\w+)\}\}'
        
        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.context_vars:
                return self.context_vars[var_name]
            return match.group(0)  # Return original if not found
        
        return re.sub(pattern, replace_var, text)
    
    def substitute_variables(self, text: str) -> str:
        """Public alias for backward compatibility."""
        return self._substitute_variables(text)
    
    def get_csrf_token(self) -> str:
        """Get CSRF token from the server."""
        if self.csrf_token:
            return self.csrf_token
        
        base_url = self.demo_data.get('environment', {}).get('base_url', 'http://localhost:3001')
        
        try:
            # Get login page to establish session and get CSRF token
            response = self.session.get(f"{base_url}/login")
            
            # Extract CSRF token from cookies or meta tag
            if 'csrf_token' in self.session.cookies:
                self.csrf_token = self.session.cookies['csrf_token']
            else:
                # Try to extract from HTML
                import re
                match = re.search(r'name="csrf_token".*?value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
            
            return self.csrf_token
        except Exception as e:
            print(f"{YELLOW}Warning: Could not get CSRF token: {e}{NC}")
            return ""
    
    def execute_browser_action(self, action: str, config: Dict) -> bool:
        """Execute an automated action via API (when --auto) or skip (human does UI)."""
        try:
            if action == 'sequence':
                # Execute a sequence of sub-actions
                sub_actions = config.get('actions', [])
                for sub_action in sub_actions:
                    sub_action_type = sub_action.get('action', '')
                    if not self.execute_browser_action(sub_action_type, sub_action):
                        return False
                return True
            elif action == 'api_check':
                endpoint = config.get('endpoint', '/api/health')
                return self.api_check(endpoint)
            elif action == 'api_post':
                return self.api_post(config)
            elif action == 'api_put':
                return self.api_put(config)
            elif action == 'api_get':
                return self.api_get(config)
            elif action == 'run_command':
                cmd = config.get('command', '')
                if cmd:
                    return self.run_command(cmd, label="Automated command")
                return False
            elif action == 'none':
                # No automated action needed, human performs UI action
                return True
            else:
                # Unknown action type - just show what would happen
                print(f"{CYAN}  Automated action: {action}{NC}")
                details = config.get('details', '')
                if details:
                    print(f"  {details}")
                return True
        except Exception as e:
            self.print_error(f"Automated action failed: {e}")
            return False
    
    def api_check(self, endpoint: str) -> bool:
        """Verify API endpoint responds correctly."""
        base_url = self.demo_data.get('environment', {}).get('base_url', 'http://localhost:3001')
        full_url = base_url + endpoint if endpoint.startswith('/') else endpoint
        
        print(f"  Checking API: {full_url}")
        
        try:
            response = self.session.get(full_url)
            if response.status_code == 200:
                print(f"{GREEN}  ✓ API responded: 200 OK{NC}")
                return True
            else:
                print(f"{RED}  ✗ API returned: {response.status_code}{NC}")
                return False
        except Exception as e:
            print(f"{RED}  ✗ API check failed: {e}{NC}")
            return False
    
    def api_post(self, config: Dict) -> bool:
        """Make a POST API call."""
        endpoint = self.substitute_variables(config.get('endpoint', ''))
        data = config.get('data', {})
        
        # Substitute variables in data values
        substituted_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                substituted_data[key] = self.substitute_variables(value)
            elif isinstance(value, list):
                substituted_data[key] = [self.substitute_variables(v) if isinstance(v, str) else v for v in value]
            else:
                substituted_data[key] = value
        
        base_url = self.demo_data.get('environment', {}).get('base_url', 'http://localhost:3001')
        full_url = base_url + endpoint if endpoint.startswith('/') else endpoint
        
        print(f"  POST {full_url}")
        if config.get('description'):
            print(f"  {config['description']}")
        
        # Show payload data (skip for login to avoid showing passwords)
        if substituted_data and 'password' not in substituted_data:
            print(f"  {CYAN}Payload: {json.dumps(substituted_data, indent=2)}{NC}")
        
        try:
            # Get CSRF token and add to headers
            csrf_token = self.get_csrf_token()
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            response = self.session.post(full_url, json=substituted_data, headers=headers)
            
            if response.status_code in [200, 201]:
                print(f"{GREEN}  ✓ Success: {response.status_code}{NC}")
                return True
            else:
                error_msg = f"Step {self.current_step}: POST {endpoint} failed ({response.status_code})"
                self.errors.append(error_msg)
                print(f"{RED}  ✗ Failed: {response.status_code}{NC}")
                if response.text:
                    print(f"{RED}  Error: {response.text[:200]}{NC}")
                return False
        except Exception as e:
            error_msg = f"Step {self.current_step}: POST {endpoint} exception: {e}"
            self.errors.append(error_msg)
            print(f"{RED}  ✗ API call failed: {e}{NC}")
            return False
    
    def api_put(self, config: Dict) -> bool:
        """Make a PUT API call."""
        endpoint = self.substitute_variables(config.get('endpoint', ''))
        data = config.get('data', {})
        
        # Substitute variables in data values
        substituted_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                substituted_data[key] = self.substitute_variables(value)
            elif isinstance(value, list):
                substituted_data[key] = [self.substitute_variables(v) if isinstance(v, str) else v for v in value]
            else:
                substituted_data[key] = value
        
        base_url = self.demo_data.get('environment', {}).get('base_url', 'http://localhost:3001')
        full_url = base_url + endpoint if endpoint.startswith('/') else endpoint
        
        print(f"  PUT {full_url}")
        if config.get('description'):
            print(f"  {config['description']}")
        
        # Show payload data
        if substituted_data:
            print(f"  {CYAN}Payload: {json.dumps(substituted_data, indent=2)}{NC}")
        
        try:
            # Get CSRF token and add to headers
            csrf_token = self.get_csrf_token()
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            response = self.session.put(full_url, json=substituted_data, headers=headers)
            
            if response.status_code == 200:
                print(f"{GREEN}  ✓ Success: {response.status_code}{NC}")
                return True
            else:
                error_msg = f"Step {self.current_step}: PUT {endpoint} failed ({response.status_code})"
                self.errors.append(error_msg)
                print(f"{RED}  ✗ Failed: {response.status_code}{NC}")
                if response.text:
                    print(f"{RED}  Error: {response.text[:200]}{NC}")
                return False
        except Exception as e:
            error_msg = f"Step {self.current_step}: PUT {endpoint} exception: {e}"
            self.errors.append(error_msg)
            print(f"{RED}  ✗ API call failed: {e}{NC}")
            return False
    
    def api_get(self, config: Dict) -> bool:
        """Make a GET API call."""
        endpoint = config.get('endpoint', '')
        base_url = self.demo_data.get('environment', {}).get('base_url', 'http://localhost:3001')
        full_url = base_url + endpoint if endpoint.startswith('/') else endpoint
        
        print(f"  GET {full_url}")
        if config.get('description'):
            print(f"  {config['description']}")
        
        try:
            response = self.session.get(full_url)
            
            if response.status_code == 200:
                print(f"{GREEN}  ✓ Success: {response.status_code}{NC}")
                return True
            else:
                print(f"{RED}  ✗ Failed: {response.status_code}{NC}")
                if response.text:
                    print(f"{RED}  Error: {response.text[:200]}{NC}")
                return False
        except Exception as e:
            print(f"{RED}  ✗ API call failed: {e}{NC}")
            return False
    
    def collect_artifacts(self, artifacts: Dict, step_num: int):
        """Collect logs for this step (screenshots removed - not needed)."""
        # Artifacts are now just for tracking purposes in JSON
        # Actual log files are written by the application itself
        pass
    
    def run_command(self, cmd: str, label: str = "Command") -> bool:
        """Run a shell command and return success status."""
        print(f"{CYAN}{label}: {cmd}{NC}")
        
        # Get working directory from environment config
        working_dir = self.working_dir
        
        try:
            # nosec B602 - shell=True is intentional for demo script commands
            result = subprocess.run(
                cmd,
                shell=True,  # nosec B602
                check=True,
                capture_output=False,
                text=True,
                cwd=working_dir
            )
            print(f"{GREEN}✓ Success{NC}\n")
            return True
        except subprocess.CalledProcessError as e:
            print(f"{RED}✗ Command failed (exit code {e.returncode}){NC}\n")
            return False
    
    def run_command_with_capture(self, cmd: str) -> Optional[str]:
        """Run a command and capture its output."""
        # Use consistent working directory from validate_environment
        working_dir = self.working_dir
        
        try:
            # nosec B602 - shell=True is intentional for demo script commands
            result = subprocess.run(
                cmd,
                shell=True,  # nosec B602
                check=True,
                capture_output=True,
                text=True,
                cwd=working_dir
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return None
    
    def print_header(self, text: str):
        """Print section header."""
        print(f"\n{BLUE}{'='*80}{NC}")
        print(f"{BLUE}{BOLD}{text}{NC}")
        print(f"{BLUE}{'='*80}{NC}\n")
    
    def print_step(self, step_num: int, total: int, phase: str, name: str):
        """Print step header."""
        print(f"\n{GREEN}{BOLD}[Step {step_num}/{total}] {phase}: {name}{NC}")
        print(f"{GREEN}{'-'*80}{NC}\n")
    
    def print_success(self, text: str):
        """Print success message."""
        print(f"{GREEN}✓ {text}{NC}\n")
    
    def print_error(self, text: str):
        """Print error message."""
        print(f"{RED}✗ {text}{NC}\n")
    
    def print_info(self, text: str):
        """Print info message."""
        print(f"{CYAN}ℹ {text}{NC}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Interactive demo runner for JSON demo files',
        epilog='Example: python run_demo.py --demo full_semester_workflow.json'
    )
    parser.add_argument(
        '--demo',
        required=True,
        help='Path to demo JSON file'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Run in automated mode (no pauses, browser automation)'
    )
    parser.add_argument(
        '--start-step',
        type=int,
        default=1,
        help='Resume from step N (skip steps 1 through N-1)'
    )
    parser.add_argument(
        '--fail-fast',
        action='store_true',
        help='Exit immediately on first verification failure'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Dry-run mode (show steps, run verifications, don\'t execute actions)'
    )
    
    args = parser.parse_args()
    
    # Resolve demo file path
    demo_file = Path(args.demo)
    if not demo_file.is_absolute():
        # Try relative to script directory
        demo_file = Path(__file__).parent / demo_file
    
    if not demo_file.exists():
        print(f"{RED}Error: Demo file not found: {args.demo}{NC}")
        sys.exit(1)
    
    # Create and run demo
    runner = DemoRunner(
        demo_file=demo_file,
        auto_mode=args.auto,
        start_step=args.start_step,
        fail_fast=args.fail_fast,
        verify_only=args.verify_only
    )
    
    runner.run_demo()


if __name__ == '__main__':
    main()
