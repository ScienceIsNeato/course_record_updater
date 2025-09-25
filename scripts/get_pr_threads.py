#!/usr/bin/env python3
"""
Simple utility to get unresolved PR comment threads.

Usage: python get_pr_threads.py [pr_number]
If no PR number provided, tries to detect from current branch.
"""

import json
import subprocess
import sys


def get_unresolved_threads(pr_number=None):
    """Get unresolved comment threads for a PR."""
    try:
        # Auto-detect PR number if not provided
        if not pr_number:
            try:
                result = subprocess.run(
                    ["gh", "pr", "view", "--json", "number"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                pr_data = json.loads(result.stdout)
                pr_number = pr_data.get("number")
            except:
                print(
                    "❌ Could not detect PR number. Please provide it as an argument."
                )
                return []

        # Get repository info
        repo_result = subprocess.run(
            ["gh", "repo", "view", "--json", "owner,name"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo_data = json.loads(repo_result.stdout)
        owner = repo_data.get("owner", {}).get("login", "")
        name = repo_data.get("name", "")

        # GraphQL query for unresolved review threads
        graphql_query = """
        query($owner: String!, $name: String!, $number: Int!) {
          repository(owner: $owner, name: $name) {
            pullRequest(number: $number) {
              reviewThreads(first: 50) {
                nodes {
                  id
                  isResolved
                  comments(first: 1) {
                    nodes {
                      body
                      path
                      line
                      author { login }
                      createdAt
                    }
                  }
                }
              }
            }
          }
        }
        """

        # Execute GraphQL query
        result = subprocess.run(
            [
                "gh",
                "api",
                "graphql",
                "-F",
                f"owner={owner}",
                "-F",
                f"name={name}",
                "-F",
                f"number={pr_number}",
                "-f",
                f"query={graphql_query}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)
        threads = (
            data.get("data", {})
            .get("repository", {})
            .get("pullRequest", {})
            .get("reviewThreads", {})
            .get("nodes", [])
        )

        # Filter and format unresolved threads
        unresolved = []
        for thread in threads:
            if not thread.get("isResolved", True):
                comment = thread.get("comments", {}).get("nodes", [{}])[0]
                unresolved.append(
                    {
                        "thread_id": thread.get("id"),
                        "body": (
                            comment.get("body", "")[:100] + "..."
                            if len(comment.get("body", "")) > 100
                            else comment.get("body", "")
                        ),
                        "author": comment.get("author", {}).get("login", "unknown"),
                        "path": comment.get("path"),
                        "line": comment.get("line"),
                    }
                )

        return unresolved

    except Exception as e:
        print(f"❌ Error getting PR threads: {e}")
        return []


def main():
    pr_number = None
    if len(sys.argv) > 1:
        try:
            pr_number = int(sys.argv[1])
        except ValueError:
            print("❌ PR number must be an integer")
            sys.exit(1)

    threads = get_unresolved_threads(pr_number)

    if not threads:
        print("✅ No unresolved comment threads found!")
        return

    print(f"📋 Found {len(threads)} unresolved comment thread(s):")
    print("=" * 60)

    for i, thread in enumerate(threads, 1):
        print(f"{i}. Thread ID: {thread['thread_id']}")
        print(f"   Author: {thread['author']}")
        print(f"   File: {thread['path']}:{thread['line'] or 'N/A'}")
        print(f"   Comment: {thread['body']}")
        print()


if __name__ == "__main__":
    main()
