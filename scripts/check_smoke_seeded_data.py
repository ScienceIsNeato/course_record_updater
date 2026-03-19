#!/usr/bin/env python3

import os
import re
import time

import requests


def create_authenticated_session() -> requests.Session:
    base_url = os.getenv("BASE_URL", "http://localhost:3003").rstrip("/")
    email = os.getenv("SMOKE_ADMIN_EMAIL", "siteadmin@system.local")
    password = os.getenv("SMOKE_ADMIN_PASSWORD", "SiteAdmin123!")

    session = requests.Session()
    login_page = session.get(f"{base_url}/login", timeout=10)
    csrf_match = re.search(
        r'name="csrf_token" value="([^"]+)"', login_page.text, re.IGNORECASE
    )
    meta_match = re.search(
        r'name="csrf-token" content="([^"]+)"', login_page.text, re.IGNORECASE
    )
    csrf_token = (
        csrf_match.group(1)
        if csrf_match
        else meta_match.group(1) if meta_match else None
    )
    if not csrf_token:
        raise SystemExit("Smoke seeded-data check could not find a CSRF token")

    response = session.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password, "remember_me": False},
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token,
            "Referer": f"{base_url}/login",
        },
        allow_redirects=True,
        timeout=10,
    )
    if response.status_code != 200:
        raise SystemExit(
            f"Smoke seeded-data login failed: {response.status_code} {response.text[:300]}"
        )

    dashboard = session.get(f"{base_url}/dashboard", timeout=10)
    if dashboard.status_code != 200 or "login" in dashboard.url:
        raise SystemExit(
            f"Smoke seeded-data dashboard bootstrap failed: {dashboard.status_code} {dashboard.url}"
        )
    return session


def main() -> None:
    base_url = os.getenv("BASE_URL", "http://localhost:3003").rstrip("/")
    session = create_authenticated_session()

    institutions = []
    last_body = ""
    for _ in range(5):
        response = session.get(f"{base_url}/api/institutions", timeout=10)
        if response.status_code != 200:
            raise SystemExit(
                f"Institutions endpoint failed: {response.status_code} {response.text[:300]}"
            )
        payload = response.json()
        if not payload.get("success"):
            raise SystemExit(f"Institutions API reported failure: {payload}")
        institutions = payload.get("institutions", [])
        last_body = response.text[:500]
        if institutions:
            break
        time.sleep(0.2)

    mocku_found = any(
        "MockU" in institution.get("name", "")
        or "MOCKU" in institution.get("short_name", "")
        or "Mock University" in institution.get("name", "")
        for institution in institutions
    )
    if not mocku_found:
        raise SystemExit(
            f"Seeded institution 'MockU' not found. Response body: {last_body}"
        )

    print("Smoke seeded-data verification passed")


if __name__ == "__main__":
    main()
