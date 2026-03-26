"""Unit tests for scripts/seed_db_baseline.py helper paths."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch


def _load_seed_baseline_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    script_path = root / "scripts" / "seed_db_baseline.py"
    spec = importlib.util.spec_from_file_location("seed_db_baseline", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dummy_seeder(module: Any) -> Any:
    class DummySeeder(module.BaselineSeeder):
        def seed(self) -> bool:
            return True

    return DummySeeder()


def _configure_offering_mocks(module: Any) -> tuple[Any, Any]:
    seeder = _dummy_seeder(module)
    db = Mock()
    module.database_service.db = db
    db.create_course_offering.return_value = "offering-1"
    db.create_course_section.side_effect = ["sec-1", None]
    return seeder, db


def _configure_clo_mocks(db: Any) -> None:
    db.get_course_by_id.side_effect = [
        {"course_id": "course-1", "course_number": "BIOL-101"},
        {"course_id": "course-2", "course_number": "CHEM-101"},
    ]
    db.get_course_outcomes.side_effect = [
        [],
        [{"clo_number": "1", "outcome_id": "existing-clo"}],
        [{"clo_number": "2", "outcome_id": "existing-2"}],
    ]
    db.create_course_outcome.side_effect = ["clo-1", "clo-2"]
    db.update_course_outcome.return_value = True


def test_manifest_loading_and_basic_helpers(tmp_path: Path, capsys: Any) -> None:
    module = _load_seed_baseline_module()
    seeder = _dummy_seeder(module)

    assert seeder._coerce_to_str(None) is None
    assert seeder._coerce_to_str(12) == "12"
    assert seeder._coerce_to_str("abc") == "abc"
    assert seeder._coerce_to_str(1.2) is None

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"k": "v"}), encoding="utf-8")
    assert seeder.load_manifest(None) == {}
    assert seeder.load_manifest(str(manifest)) == {"k": "v"}
    assert seeder.load_manifest(str(tmp_path / "missing.json")) == {}

    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("{oops", encoding="utf-8")
    assert seeder.load_manifest(str(bad_manifest)) == {}
    assert "[SEED]" in capsys.readouterr().out


def test_create_institutions_terms_programs_and_courses() -> None:
    module = _load_seed_baseline_module()
    seeder = _dummy_seeder(module)
    db = Mock()
    module.database_service.db = db

    db.get_institution_by_short_name.side_effect = [
        None,
        {"institution_id": "inst-existing"},
    ]
    db.create_institution.return_value = "inst-new"
    institution_ids = seeder.create_institutions_from_manifest(
        [
            {"name": "New Inst", "short_name": "NEW", "logo_path": "/logo.png"},
            {"name": "Existing", "short_name": "EX"},
        ]
    )
    assert institution_ids == ["inst-new", "inst-existing"]

    db.create_term.side_effect = ["term-1", "term-2", "term-3", None]
    term_ids = seeder.create_terms_from_manifest(
        ["inst-1", "inst-2"],
        [
            {
                "name": "Fall 2025",
                "start_date": "2025-08-01T00:00:00",
                "end_date": "2025-12-01T00:00:00",
            },
            {"name": "Broken", "start_date": "bad", "end_date": "still-bad"},
        ],
    )
    assert term_ids == ["term-1", "term-2", "term-3"]

    db.create_program.side_effect = ["prog-1", "prog-2"]
    program_ids = seeder.create_programs_from_manifest(
        ["inst-1", "inst-2"],
        [
            {"name": "Biology", "code": "BIOL"},
            {"name": "Chemistry", "institution_idx": 1},
        ],
    )
    assert program_ids == ["prog-1", "prog-2"]

    db.get_program_by_id.side_effect = [
        {"institution_id": "inst-1"},
        {"institution_id": "inst-2"},
    ]
    db.create_course.side_effect = ["course-1", "course-2"]
    course_ids = seeder.create_courses_from_manifest(
        ["inst-1", "inst-2"],
        [
            {"code": "BIOL-101", "name": "Biology", "program_code": "BIOL"},
            {"code": "CHEM-101", "name": "Chem", "program_idx": 1},
            {"code": "SKIP-1", "name": "Skip Me"},
        ],
        {"BIOL": "prog-1", "CHEM": "prog-2"},
    )
    assert course_ids == ["course-1"]

    course_ids_2 = seeder.create_courses_from_manifest(
        ["inst-1", "inst-2"],
        [{"code": "CHEM-101", "name": "Chem", "program_idx": 1}],
        ["prog-1", "prog-2"],
    )
    assert course_ids_2 == ["course-2"]


def test_user_resolution_and_creation(monkeypatch: Any) -> None:
    module = _load_seed_baseline_module()
    seeder = _dummy_seeder(module)
    db = Mock()
    module.database_service.db = db

    import src.utils.constants as constants

    monkeypatch.setattr(constants, "TEST_USER_EMAIL", "env@example.com", raising=False)
    monkeypatch.setattr(constants, "TEST_PASSWORD", "clear-secret", raising=False)
    db.get_user_by_email.side_effect = [None, {"user_id": "existing"}]
    db.create_user.return_value = "new-user"

    with patch.object(module, "hash_password", return_value="hashed-secret"):
        user_ids = seeder.create_users_from_manifest(
            ["inst-1", "inst-2"],
            [
                {
                    "email_env_var": "TEST_USER_EMAIL",
                    "password_env_var": "TEST_PASSWORD",
                    "first_name": "Env",
                    "last_name": "User",
                    "role": "site_admin",
                    "program_code": "BIOL",
                    "system_date_override": "2025-01-01T00:00:00",
                },
                {
                    "email": "existing@example.com",
                    "first_name": "Existing",
                    "last_name": "User",
                },
                {
                    "email_env_var": "MISSING_ENV_VAR",
                    "first_name": "Skip",
                    "last_name": "User",
                },
            ],
            {"BIOL": "prog-1"},
            "fallback-hash",
        )

    assert user_ids == ["new-user", "existing", None]
    schema = db.create_user.call_args.args[0]
    assert schema["email"] == "env@example.com"
    assert schema["institution_id"] == str(module.SITE_ADMIN_INSTITUTION_ID)
    assert schema["program_ids"] == ["prog-1"]
    assert schema["password_hash"] == "hashed-secret"

    assert (
        seeder._resolve_user_email({"email": "direct@example.com"})
        == "direct@example.com"
    )
    assert (
        seeder._resolve_user_email({"email_env_var": "TEST_USER_EMAIL"})
        == "env@example.com"
    )
    assert seeder._resolve_user_program_ids({"program_idx": 0}, None, ["prog-1"]) == [
        "prog-1"
    ]
    assert seeder._resolve_user_program_ids(
        {"program_code": "BIOL"}, {"BIOL": "prog-1"}, None
    ) == ["prog-1"]


def test_offering_helpers_and_clo_creation() -> None:
    module = _load_seed_baseline_module()
    seeder, db = _configure_offering_mocks(module)

    offerings = seeder.create_offerings_from_manifest(
        "inst-1",
        {"T1": "term-1"},
        [
            {"_comment": "skip"},
            {
                "course_code": "BIOL-101",
                "term_code": "T1",
                "sections": [
                    {"section_number": "001", "instructor_idx": 0, "enrollment": 10},
                    {"section_number": "002", "instructor_idx": 4, "enrollment": 8},
                ],
            },
            {"course_code": "UNKNOWN", "sections": []},
        ],
        {"BIOL-101": "course-1"},
        ["inst-user-1"],
    )
    assert offerings == {"offering_ids": ["offering-1"], "section_count": 1}
    assert seeder._resolve_course_id_from_manifest({"course_id": 99}, {}) == "99"
    assert seeder._resolve_term_id_from_manifest({"_term_id": "t2"}, None, {}) == "t2"
    assert seeder._resolve_term_id_from_manifest({}, "t1", {}) == "t1"
    assert seeder._resolve_section_instructor({"instructor_idx": 0}, ["u1"]) == "u1"
    assert seeder._resolve_section_instructor({"instructor_idx": 2}, ["u1"]) is None

    _configure_clo_mocks(db)

    with patch.dict(
        "sys.modules",
        {
            "src.utils.constants": SimpleNamespace(
                CLOStatus=SimpleNamespace(
                    ASSIGNED="assigned",
                    UNASSIGNED="unassigned",
                    APPROVED="approved",
                    COMPLETED="completed",
                    NEVER_COMING_IN="never_coming_in",
                    AWAITING_APPROVAL="awaiting_approval",
                ),
                CLOApprovalStatus=SimpleNamespace(
                    APPROVED="approved",
                    NEEDS_REWORK="needs_rework",
                    NEVER_COMING_IN="never_coming_in",
                    PENDING="pending",
                ),
            )
        },
    ):
        created_count = seeder.create_clos_from_manifest(
            ["course-1", "course-2"],
            {
                "clo_templates": {
                    "BIOL": [{"num": 1, "desc": "Desc", "method": "Exam"}],
                },
                "clos": [
                    {
                        "course_code": "CHEM-101",
                        "clo_number": 2,
                        "description": "Specific desc",
                        "assessment_method": "Lab",
                        "status": "approved",
                        "submitted_at": "2025-01-01T00:00:00",
                        "students_took": 10,
                        "students_passed": 8,
                        "assessment_tool": "Final",
                    },
                    {"course_code": "MISSING", "clo_number": 9},
                ],
            },
        )

    assert created_count == 1
    db.update_course_outcome.assert_called_once()
    assert db.update_course_outcome.call_args.args[0] == "existing-2"
    updates = db.update_course_outcome.call_args.args[1]
    assert updates["status"] == "approved"
    assert updates["approval_status"] == "approved"
    assert updates["submitted_at"] is not None
    assert updates["students_took"] == 10
    assert updates["students_passed"] == 8
    assert updates["assessment_tool"] == "Final"
    assert updates["percentage_meeting"] == 80.0
    assert seeder._parse_submitted_at("approved", "bad-date") is None
