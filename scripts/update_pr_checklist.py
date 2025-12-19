#!/usr/bin/env python3
"""
update_pr_checklist.py - Update PR issues checklist as items are completed

Usage:
    # Mark an item as complete (optionally reply to PR comment)
    python scripts/update_pr_checklist.py --complete "Fix failing CI job: e2e-tests"
    python scripts/update_pr_checklist.py --complete "Address comment from ScienceIsNeato" --reply-to-comment --thread-id PRRT_xxx
    
    # Mark an item as in-progress
    python scripts/update_pr_checklist.py --in-progress "Address comment from ScienceIsNeato"
    
    # Show current checklist status
    python scripts/update_pr_checklist.py --status
    
    # Reset checklist (for new report)
    python scripts/update_pr_checklist.py --reset
"""

import argparse
import json
import os
import subprocess  # nosec B404
import sys
from pathlib import Path


def get_pr_number():
    """Get current PR number from git context."""
    try:
        result = subprocess.run(  # nosec
            ["gh", "pr", "view", "--json", "number"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return data.get("number")
    except Exception:  # nosec B110 - return None if not in PR context
        return None


def get_current_commit():
    """Get current commit SHA."""
    try:
        result = subprocess.run(  # nosec
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:8]
    except Exception:  # nosec B110 - return None if git command fails
        return None


def get_checklist_state_file(pr_number, commit_sha):
    """Get path to checklist state file."""
    os.makedirs("logs", exist_ok=True)
    return f"logs/pr_{pr_number}_checklist_state_{commit_sha}.json"


def load_checklist_state(pr_number, commit_sha):
    """Load checklist state from file."""
    state_file = get_checklist_state_file(pr_number, commit_sha)
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # nosec B110 - fallback to empty state if file corrupted
            pass
    
    return {
        "pr_number": pr_number,
        "commit_sha": commit_sha,
        "items": {},
        "last_updated": None,
    }


def save_checklist_state(state):
    """Save checklist state to file."""
    state_file = get_checklist_state_file(state["pr_number"], state["commit_sha"])
    from datetime import datetime
    state["last_updated"] = datetime.now().isoformat()
    
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    
    return state_file


def find_checklist_item(state, item_text):
    """Find checklist item by text (fuzzy match)."""
    item_text_lower = item_text.lower()
    
    for item_id, item_data in state["items"].items():
        if item_text_lower in item_data.get("text", "").lower():
            return item_id, item_data
    
    # If not found, create new entry
    item_id = f"item_{len(state['items']) + 1}"
    return item_id, {"text": item_text, "status": "pending"}


def update_item_status(state, item_text, status):
    """Update status of a checklist item."""
    item_id, item_data = find_checklist_item(state, item_text)
    item_data["status"] = status
    item_data["text"] = item_text  # Update text in case it was fuzzy matched
    state["items"][item_id] = item_data
    return item_id


def print_status(state):
    """Print current checklist status."""
    print(f"\n📋 PR #{state['pr_number']} Checklist Status (Commit: {state['commit_sha'][:8]})\n")
    
    completed = [item for item in state["items"].values() if item["status"] == "completed"]
    in_progress = [item for item in state["items"].values() if item["status"] == "in_progress"]
    pending = [item for item in state["items"].values() if item["status"] == "pending"]
    
    print(f"✅ Completed: {len(completed)}")
    print(f"🔄 In Progress: {len(in_progress)}")
    print(f"⏳ Pending: {len(pending)}")
    print(f"📊 Total: {len(state['items'])}\n")
    
    if in_progress:
        print("🔄 In Progress:")
        for item in in_progress:
            print(f"  • {item['text']}")
        print()
    
    if pending:
        print("⏳ Pending:")
        for item in pending[:10]:  # Show first 10
            print(f"  • {item['text']}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")
        print()
    
    if completed:
        print(f"✅ Completed ({len(completed)} items)")
        print()


def _setup_parser():
    """Setup argument parser."""
    parser = argparse.ArgumentParser(
        description="Update PR issues checklist as items are completed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--complete",
        metavar="ITEM",
        help="Mark an item as completed",
    )
    
    parser.add_argument(
        "--in-progress",
        metavar="ITEM",
        dest="in_progress",
        help="Mark an item as in-progress",
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current checklist status",
    )
    
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset checklist state (for new report)",
    )
    
    parser.add_argument(
        "--pr",
        type=int,
        help="PR number (default: auto-detect)",
    )
    
    parser.add_argument(
        "--commit",
        help="Commit SHA (default: current HEAD)",
    )
    
    parser.add_argument(
        "--reply-to-comment",
        action="store_true",
        help="Reply to PR comment when marking item complete (requires --thread-id or --comment-id)",
    )
    
    parser.add_argument(
        "--thread-id",
        help="Review thread ID (for inline comments, used with --reply-to-comment)",
    )
    
    parser.add_argument(
        "--comment-id",
        help="Comment ID (for general PR comments, used with --reply-to-comment)",
    )
    return parser


def _handle_completion(state, args):
    """Handle item completion and optional PR comment reply."""
    update_item_status(state, args.complete, "completed")
    save_checklist_state(state)
    
    # If --reply-to-comment is specified, reply to the PR comment
    if args.reply_to_comment:
        if not args.thread_id and not args.comment_id:
            print("❌ Error: --reply-to-comment requires --thread-id or --comment-id")
            return 1
        
        # Import reply function
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        try:
            from scripts.ship_it import reply_to_pr_comment

            # Create reply body with commit reference
            commit_sha_full = subprocess.run(  # nosec
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            
            reply_body = f"Fixed in commit `{commit_sha_full[:8]}`"
            
            # Reply and resolve thread
            success = reply_to_pr_comment(
                comment_id=args.comment_id,
                body=reply_body,
                thread_id=args.thread_id,
                resolve_thread=True if args.thread_id else False,
            )
            
            if success:
                print(f"✅ Replied to PR comment and marked as resolved")
            else:
                print(f"⚠️  Failed to reply to PR comment, but item marked as complete")
        except Exception as e:
            print(f"⚠️  Error replying to PR comment: {e}")
            print(f"✅ Item marked as completed locally")
    
    print(f"✅ Marked as completed: {args.complete}")
    return 0


def main():
    parser = _setup_parser()
    args = parser.parse_args()
    
    pr_number = args.pr or get_pr_number()
    commit_sha = args.commit or get_current_commit()
    
    if not pr_number:
        print("❌ Error: Not in a PR context. Cannot determine PR number.")
        return 1
    
    if not commit_sha:
        print("❌ Error: Cannot determine commit SHA.")
        return 1
    
    state = load_checklist_state(pr_number, commit_sha)
    
    if args.reset:
        state = {
            "pr_number": pr_number,
            "commit_sha": commit_sha,
            "items": {},
            "last_updated": None,
        }
        save_checklist_state(state)
        print("✅ Checklist reset")
        return 0
    
    if args.complete:
        return _handle_completion(state, args)
    
    if args.in_progress:
        update_item_status(state, args.in_progress, "in_progress")
        save_checklist_state(state)
        print(f"🔄 Marked as in-progress: {args.in_progress}")
        return 0
    
    if args.status:
        print_status(state)
        return 0
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

