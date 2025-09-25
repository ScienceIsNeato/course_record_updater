#!/usr/bin/env python3
"""
Simple utility to resolve a GitHub PR comment thread.

Usage: python resolve_conversation.py <thread_id>
"""

import json
import subprocess
import sys


def resolve_thread(thread_id):
    """Resolve a single GitHub PR comment thread using GraphQL."""
    try:
        mutation = f"""
        mutation {{
          resolveReviewThread(input: {{ threadId: "{thread_id}" }}) {{
            clientMutationId
          }}
        }}
        """

        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={mutation}"],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)

        if data.get("data", {}).get("resolveReviewThread"):
            print(f"✅ Resolved thread: {thread_id}")
            return True
        else:
            print(f"❌ Failed to resolve thread: {thread_id}")
            if "errors" in data:
                for error in data["errors"]:
                    print(f"   Error: {error.get('message', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Error resolving thread {thread_id}: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python resolve_conversation.py <thread_id>")
        sys.exit(1)

    thread_id = sys.argv[1]
    success = resolve_thread(thread_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
