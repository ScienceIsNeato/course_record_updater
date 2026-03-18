"""Unit coverage for tests/e2e/email_utils.py utilities."""

from __future__ import annotations

import importlib.util
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest


def _load_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    file_path = root / "tests" / "e2e" / "email_utils.py"
    spec = importlib.util.spec_from_file_location("email_utils", file_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mailtrap_auth_and_api_calls(monkeypatch: Any) -> None:
    module = _load_module()

    monkeypatch.setenv("MAILTRAP_API_USERNAME", "u")
    monkeypatch.setenv("MAILTRAP_API_PASSWORD", "p")
    assert module.get_mailtrap_auth() == ("u", "p")

    monkeypatch.delenv("MAILTRAP_API_PASSWORD", raising=False)
    with pytest.raises(module.MailtrapError):
        module.get_mailtrap_auth()


@patch("requests.get")
def test_get_inbox_emails_and_filters(mock_get: Any) -> None:
    module = _load_module()
    payload = [
        {"subject": "Welcome", "to_email": "x@test.edu"},
        {"subject": "Reset Password", "to_email": "y@test.edu, x@test.edu"},
    ]
    mock_resp = Mock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    with patch.object(module, "get_mailtrap_auth", return_value=("u", "p")):
        emails = module.get_inbox_emails("box-1")
        assert len(emails) == 2
        assert module.get_email_by_recipient("x@test.edu", "box-1") is not None
        assert module.get_email_by_subject("reset", "box-1") is not None


@patch("requests.get")
def test_get_inbox_emails_request_error(mock_get: Any) -> None:
    module = _load_module()
    mock_get.side_effect = module.requests.exceptions.RequestException("boom")

    with patch.object(module, "get_mailtrap_auth", return_value=("u", "p")):
        with pytest.raises(module.MailtrapError):
            module.get_inbox_emails("box-1")


def test_wait_for_email_delegation_and_legacy_paths() -> None:
    module = _load_module()

    with patch.object(
        module, "wait_for_email_via_imap", return_value={"ok": True}
    ) as p:
        result = module.wait_for_email("x@test.edu", subject_substring="S", timeout=5)
        assert result == {"ok": True}
        p.assert_called_once()

    with patch.object(module, "get_email_by_recipient", return_value={"subject": "A"}):
        found = module._wait_for_email_mailtrap_legacy(
            "x@test.edu", subject_substring="A", timeout=1, poll_interval=0.01
        )
        assert found is not None


def test_link_extractors_and_token_parsing() -> None:
    module = _load_module()

    email_dict = {
        "html_body": '<a href="https://x.test/api/auth/verify-email/tok123">v</a>',
        "text_body": "reset at https://x.test/reset-password/tok456",
    }
    assert module.extract_verification_link(email_dict) is not None
    assert module.extract_reset_link(email_dict) is not None
    assert module.extract_token_from_url("https://x.test?a=1&token=abc") == "abc"

    v2 = module.extract_verification_link_from_email(
        {"body": "https://x.test/verify-email?token=t1", "html_body": ""}
    )
    r2 = module.extract_password_reset_link_from_email(
        {"body": "https://x.test/reset-password?token=t2", "html_body": ""}
    )
    assert v2 is not None
    assert r2 is not None


@patch("requests.patch")
def test_delete_and_verify_email_content(mock_patch: Any) -> None:
    module = _load_module()

    ok_resp = Mock()
    ok_resp.raise_for_status.return_value = None
    mock_patch.return_value = ok_resp

    with patch.object(module, "get_mailtrap_auth", return_value=("u", "p")):
        module.delete_all_emails("box-1")

    email_data = {
        "subject": "Verify",
        "to_email": "a@test.edu",
        "html_body": "hello token",
        "text_body": "hello",
    }
    assert module.verify_email_content(
        email_data,
        expected_subject="Verify",
        expected_recipient="a@test.edu",
        expected_text_snippets=["token"],
    )
    assert not module.verify_email_content(email_data, expected_subject="Wrong")


def test_ethereal_inbox_clear_paths(monkeypatch: Any) -> None:
    module = _load_module()

    monkeypatch.setattr(module, "USE_ETHEREAL_IMAP", False)
    assert module.clear_ethereal_inbox() is False

    monkeypatch.setattr(module, "USE_ETHEREAL_IMAP", True)
    monkeypatch.setattr(module, "ETHEREAL_USER", "u")
    monkeypatch.setattr(module, "ETHEREAL_PASS", "p")

    mail = Mock()
    mail.search.return_value = ("OK", [b"1 2"])
    with patch.object(module.imaplib, "IMAP4_SSL", return_value=mail):
        assert module.clear_ethereal_inbox() is True
        assert mail.store.call_count == 2
        mail.expunge.assert_called_once()


def test_parse_and_match_helpers() -> None:
    module = _load_module()

    msg = EmailMessage()
    msg["Subject"] = "Verify Me"
    msg["To"] = "User <u@test.edu>"
    msg["From"] = "noreply@test.edu"
    msg.set_content("body token-1")
    msg.add_alternative("<p>html token-1</p>", subtype="html")

    body, html = module._extract_body_content(msg)
    assert "token-1" in body
    assert "token-1" in html

    assert module._check_recipient(msg, "u@test.edu")

    wrapped = [(b"RFC822", msg.as_bytes())]
    result = module._parse_and_match_email(
        wrapped,
        recipient_email="u@test.edu",
        subject_substring="Verify",
        unique_identifier="token-1",
    )
    assert result is not None

    no_match = module._parse_and_match_email(
        wrapped,
        recipient_email="z@test.edu",
        subject_substring="Verify",
        unique_identifier=None,
    )
    assert no_match is None


def test_wait_for_email_via_imap_paths(monkeypatch: Any) -> None:
    module = _load_module()

    monkeypatch.setattr(module, "USE_ETHEREAL_IMAP", False)
    assert module.wait_for_email_via_imap("u@test.edu") is None

    monkeypatch.setattr(module, "USE_ETHEREAL_IMAP", True)
    monkeypatch.setattr(module, "ETHEREAL_USER", "u")
    monkeypatch.setattr(module, "ETHEREAL_PASS", "p")

    # Success path
    mail = Mock()
    mail.search.return_value = ("OK", [b"1"])
    mail.fetch.return_value = ("OK", [(b"RFC822", EmailMessage().as_bytes())])

    with (
        patch.object(module.imaplib, "IMAP4_SSL", return_value=mail),
        patch.object(
            module,
            "_parse_and_match_email",
            return_value={"subject": "S", "to": "u@test.edu"},
        ),
    ):
        result = module.wait_for_email_via_imap(
            "u@test.edu", timeout=1, poll_interval=1
        )
        assert result is not None

    # Abort/retry path with timeout
    with (
        patch.object(
            module.imaplib, "IMAP4_SSL", side_effect=module.imaplib.IMAP4.abort("x")
        ),
        patch.object(module.time, "sleep"),
    ):
        miss = module.wait_for_email_via_imap("u@test.edu", timeout=1, poll_interval=1)
        assert miss is None
