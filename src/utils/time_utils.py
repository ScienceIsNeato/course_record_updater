"""Time utilities for system date override.

Provides get_current_time() which respects per-user date overrides.
This allows admins to "time travel" for demos and testing.
"""

from datetime import datetime, timezone

from flask import g


def get_current_time() -> datetime:
    """Get current time, respecting user's date override if set.

    Returns:
        datetime: Current time in UTC. If the logged-in user has
        system_date_override set, returns that instead of real time.

    Priority:
        1. User's system_date_override (if set)
        2. Real datetime.now(timezone.utc)
    """
    # Check if we have a logged-in user with an override
    try:
        # 1. Check direct global override (set by middleware or tests)
        if hasattr(g, "system_date_override") and g.system_date_override:
            return g.system_date_override

        # 2. Check logged-in user (fallback to support legacy object access or direct dict access)
        current_user = getattr(g, "current_user", None)
        if current_user is not None:
            # Handle object-style access
            override = getattr(current_user, "system_date_override", None)
            if override:
                return override

            # Handle dict-style access (production auth_service returns dict)
            if isinstance(current_user, dict):
                override = current_user.get("system_date_override")
                if override:
                    return override
    except RuntimeError:
        # Outside of request context - use real time
        pass

    return datetime.now(timezone.utc)
