#!/usr/bin/env python3
"""
Interactive Demo Runner

Parses a markdown demo file and provides interactive step-by-step guidance.

Usage:
    python run_demo.py <demo_file.md>
    python run_demo.py single_term_outcome_management.md

Features:
    - Parses markdown sections
    - Displays instructions step-by-step
    - Waits for signal to continue (named pipe for agent/human)
    - Runs setup commands automatically (with confirmation)
    - Tracks progress through demo

Agent/Human Communication:
    Script creates a named pipe (FIFO) at /tmp/demo_continue.fifo
    To continue to next step:
        echo "continue" > /tmp/demo_continue.fifo
    Or from Python:
        with open('/tmp/demo_continue.fifo', 'w') as f:
            f.write('continue\\n')

Contract for Demo Markdown Files:
    - ## Setup section with bash code blocks
    - ### Step N: Title sections for each step
    - **Press Enter to continue →** markers for pauses
    - Clear instructions for what to expect and do
"""

import argparse
import os
import re
import subprocess
import sys
import signal
from pathlib import Path
from typing import List, Tuple

# ANSI color codes
BLUE = '\033[0;34m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
NC = '\033[0m'  # No Color

# Named pipe for agent/human communication
FIFO_PATH = '/tmp/demo_continue.fifo'

# Global timeout (seconds) - prevent hanging forever
GLOBAL_TIMEOUT = 300  # 5 minutes


def timeout_handler(signum, frame):
    """Handle timeout - cleanup and exit"""
    print(f"\n{YELLOW}⏰ Demo timeout reached ({GLOBAL_TIMEOUT}s). Cleaning up...{NC}")
    cleanup_fifo()
    sys.exit(1)


def print_header(text: str) -> None:
    """Print section header"""
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}{BOLD}{text}{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")


def print_step(step_num: int, title: str) -> None:
    """Print step header"""
    print(f"\n{GREEN}{BOLD}[Step {step_num}] {title}{NC}")
    print(f"{GREEN}{'-'*70}{NC}\n")


def print_instruction(text: str) -> None:
    """Print instruction text"""
    # Clean up markdown formatting for display
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove italic
    print(text)


def parse_demo_file(filepath: str) -> Tuple[dict, List[dict]]:
    """
    Parse demo markdown file into setup and steps.
    
    Returns:
        (setup_dict, steps_list)
        - setup_dict: {'commands': [list of bash commands]}
        - steps_list: [{'num': 1, 'title': 'Login', 'content': '...', 'pause': True}, ...]
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    setup = {'commands': []}
    steps = []
    
    # Extract setup section
    setup_match = re.search(r'## Setup\n\n```bash\n(.*?)\n```', content, re.DOTALL)
    if setup_match:
        command_text = setup_match.group(1)
        # Split by lines, filter out comments and empty lines
        commands = [
            line.strip() 
            for line in command_text.split('\n') 
            if line.strip() and not line.strip().startswith('#')
        ]
        setup['commands'] = commands
    
    # Extract steps (### Step N: Title)
    step_pattern = r'### Step (\d+): (.*?)\n\n(.*?)(?=### Step|\Z)'
    step_matches = re.finditer(step_pattern, content, re.DOTALL)
    
    for match in step_matches:
        step_num = int(match.group(1))
        step_title = match.group(2).strip()
        step_content = match.group(3).strip()
        
        # Check if step has pause marker
        has_pause = '**Press Enter to continue →**' in step_content
        
        # Remove pause marker from content
        step_content = step_content.replace('**Press Enter to continue →**', '').strip()
        
        steps.append({
            'num': step_num,
            'title': step_title,
            'content': step_content,
            'pause': has_pause
        })
    
    return setup, steps


def run_setup(setup: dict) -> bool:
    """
    Run setup commands with user confirmation.
    
    Returns:
        True if successful, False otherwise
    """
    if not setup['commands']:
        return True
    
    print_header("Demo Setup")
    print("The following commands will prepare the demo environment:\n")
    
    for i, cmd in enumerate(setup['commands'], 1):
        print(f"  {i}. {CYAN}{cmd}{NC}")
    
    print(f"\n{YELLOW}Send 'y' to run setup commands, or 'n' to skip:{NC}")
    with open(FIFO_PATH, 'r') as fifo:
        response = fifo.read().strip().lower()
        print(f"{GREEN}✓ Received: {response}{NC}\n")
    
    if response != 'y':
        print(f"{YELLOW}Setup skipped. Make sure environment is prepared manually.{NC}\n")
        return True
    
    print()
    for cmd in setup['commands']:
        print(f"{CYAN}Running: {cmd}{NC}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                capture_output=False,
                text=True
            )
            print(f"{GREEN}✓ Success{NC}\n")
        except subprocess.CalledProcessError as e:
            print(f"{YELLOW}✗ Command failed (exit code {e.returncode}){NC}\n")
            print(f"{YELLOW}Send 'y' to continue anyway, or 'n' to abort:{NC}")
            with open(FIFO_PATH, 'r') as fifo:
                response = fifo.read().strip().lower()
                print(f"{GREEN}✓ Received: {response}{NC}\n")
            if response != 'y':
                return False
    
    print(f"{GREEN}Setup complete!{NC}\n")
    return True


def create_fifo():
    """Create named pipe for communication"""
    # Remove existing pipe if present
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)
    
    # Create new named pipe
    os.mkfifo(FIFO_PATH)
    print(f"{CYAN}Created control pipe: {FIFO_PATH}{NC}")
    print(f"{CYAN}To continue: echo 'continue' > {FIFO_PATH}{NC}\n")


def cleanup_fifo():
    """Remove named pipe"""
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)


def wait_for_continue():
    """Block until signal received via named pipe"""
    print(f"{YELLOW}Waiting for continue signal...{NC}")
    print(f"{YELLOW}Run: echo 'continue' > {FIFO_PATH}{NC}\n")
    
    try:
        with open(FIFO_PATH, 'r') as fifo:
            message = fifo.read().strip()
            if message:
                print(f"{GREEN}✓ Received signal: {message}{NC}\n")
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Demo interrupted by user{NC}")
        cleanup_fifo()
        sys.exit(0)


def run_demo(filepath: str) -> None:
    """Run interactive demo from markdown file"""
    # Set global timeout to prevent hanging
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(GLOBAL_TIMEOUT)
    
    # Parse demo file
    try:
        setup, steps = parse_demo_file(filepath)
    except FileNotFoundError:
        print(f"{YELLOW}Error: Demo file not found: {filepath}{NC}")
        sys.exit(1)
    except Exception as e:
        print(f"{YELLOW}Error parsing demo file: {e}{NC}")
        sys.exit(1)
    
    # Get demo name from filename
    demo_name = Path(filepath).stem.replace('_', ' ').title()
    
    print_header(f"Interactive Demo: {demo_name}")
    print("This script will guide you through the demo step-by-step.")
    print("At each pause, send a signal via the named pipe to continue.")
    print(f"Global timeout: {GLOBAL_TIMEOUT}s\n")
    
    # Create named pipe for communication
    create_fifo()
    
    print(f"{YELLOW}Ready to begin. Send continue signal...{NC}\n")
    wait_for_continue()
    
    # Run setup
    if not run_setup(setup):
        print(f"{YELLOW}Setup failed. Exiting.{NC}")
        sys.exit(1)
    
    # Run through steps
    try:
        for step in steps:
            print_step(step['num'], step['title'])
            print_instruction(step['content'])
            
            if step['pause']:
                wait_for_continue()
        
        # Demo complete
        print_header("Demo Complete!")
        print(f"{GREEN}You've successfully completed the demo.{NC}\n")
        print("Key takeaways:")
        print("  • End-to-end workflow demonstrated")
        print("  • All major features showcased")
        print("  • Ready to discuss next steps\n")
    finally:
        # Always clean up the pipe
        cleanup_fifo()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Interactive demo runner for markdown demo files',
        epilog='Example: python run_demo.py single_term_outcome_management.md'
    )
    parser.add_argument(
        'demo_file',
        help='Path to markdown demo file'
    )
    parser.add_argument(
        '--no-setup',
        action='store_true',
        help='Skip setup commands'
    )
    
    args = parser.parse_args()
    
    # Resolve path relative to script location
    script_dir = Path(__file__).parent
    demo_file = Path(args.demo_file)
    
    # If not absolute, try relative to parent directory (workflow-walkthroughs/)
    if not demo_file.is_absolute():
        demo_file = script_dir.parent / demo_file
    
    if not demo_file.exists():
        # Try in current directory
        demo_file = Path(args.demo_file)
    
    if not demo_file.exists():
        print(f"{YELLOW}Error: Demo file not found: {args.demo_file}{NC}")
        print(f"Searched:")
        print(f"  - {script_dir.parent / args.demo_file}")
        print(f"  - {Path(args.demo_file).absolute()}")
        sys.exit(1)
    
    run_demo(str(demo_file))


if __name__ == '__main__':
    main()

