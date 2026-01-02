#!/usr/bin/env python3
"""
reply_to_pr_comment.py - Reply to PR comments and auto-resolve threads

Usage:
    # Reply to a review thread (inline comment) and auto-resolve
    python scripts/reply_to_pr_comment.py --thread-id PRRT_xxx --body "Fixed in commit abc123"

    # Reply to a general PR comment
    python scripts/reply_to_pr_comment.py --comment-id IC_xxx --body "Thanks for the feedback!"

    # Reply without auto-resolving (for review threads)
    python scripts/reply_to_pr_comment.py --thread-id PRRT_xxx --body "Working on it..." --no-resolve
"""

import argparse
import os
import sys

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from scripts.ship_it import reply_to_pr_comment


def main():
    parser = argparse.ArgumentParser(
        description="Reply to PR comments and optionally auto-resolve threads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reply to review thread and auto-resolve
  python scripts/reply_to_pr_comment.py --thread-id PRRT_kwDOOV6J2s5g4yRA --body "Fixed in commit abc123"
  
  # Reply to general comment
  python scripts/reply_to_pr_comment.py --comment-id IC_xxx --body "Thanks!"
  
  # Reply without resolving
  python scripts/reply_to_pr_comment.py --thread-id PRRT_xxx --body "Working on it..." --no-resolve
        """,
    )

    parser.add_argument(
        "--thread-id",
        help="Review thread ID (for inline comments)",
    )

    parser.add_argument(
        "--comment-id",
        help="Comment ID (for general PR comments)",
    )

    parser.add_argument(
        "--body",
        required=True,
        help="Reply body text",
    )

    parser.add_argument(
        "--body-file",
        help="Read reply body from file (use - for stdin)",
    )

    parser.add_argument(
        "--no-resolve",
        action="store_true",
        help="Don't auto-resolve the thread (only applies to review threads)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.thread_id and not args.comment_id:
        parser.error("Must provide either --thread-id or --comment-id")

    if args.thread_id and args.comment_id:
        parser.error("Cannot provide both --thread-id and --comment-id")

    # Get body text
    body = args.body
    if args.body_file:
        if args.body_file == "-":
            body = sys.stdin.read()
        else:
            with open(args.body_file, "r", encoding="utf-8") as f:
                body = f.read()

    if not body.strip():
        print("❌ Error: Reply body cannot be empty")
        return 1

    # Reply to comment
    resolve_thread = not args.no_resolve if args.thread_id else False

    success = reply_to_pr_comment(
        comment_id=args.comment_id,
        body=body,
        thread_id=args.thread_id,
        resolve_thread=resolve_thread,
    )

    if success:
        action = "replied to"
        if args.thread_id and resolve_thread:
            action = "replied to and resolved"
        print(f"✅ Successfully {action} comment")
        return 0
    else:
        print("❌ Failed to reply to comment")
        return 1


if __name__ == "__main__":
    sys.exit(main())
