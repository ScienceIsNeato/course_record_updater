"""Unit tests for scripts/advance_demo.py."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import pytest


def _load_advance_demo_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    script_path = root / "scripts" / "advance_demo.py"
    spec = importlib.util.spec_from_file_location("advance_demo", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_env_sets_expected_database_url(monkeypatch: Any) -> None:
    module = _load_advance_demo_module()

    module.setup_env("e2e")
    assert module.os.environ["DATABASE_URL"] == "sqlite:///loopcloser_e2e.db"
    assert module.os.environ["FLASK_ENV"] == "development"

    module.setup_env("unknown")
    assert module.os.environ["DATABASE_URL"] == "sqlite:///loopcloser_dev.db"


def test_run_generate_logs_handles_missing_admin() -> None:
    module = _load_advance_demo_module()
    db = Mock()
    db.get_user_by_email.return_value = None

    module.run_generate_logs(Mock(), db)

    db.get_user_by_email.assert_called_once_with("demo2025.admin@example.com")


def test_run_generate_logs_invites_and_imports(tmp_path: Path) -> None:
    module = _load_advance_demo_module()
    db = Mock()
    db.get_user_by_email.side_effect = [
        {
            "user_id": "admin-1",
            "email": "demo2025.admin@example.com",
            "institution_id": "inst-1",
        },
        None,
    ]

    invitation_service = Mock()
    invitation_service.create_invitation.return_value = {"token": "abc"}
    invitation_service.send_invitation.return_value = (True, None)
    import_service_cls = Mock()
    import_service = Mock()
    import_service.import_excel_file.return_value = SimpleNamespace(
        success=True,
        records_created=2,
        records_updated=1,
        errors=[],
    )
    import_service_cls.return_value = import_service

    original_cwd = Path.cwd()
    try:
        module.os.chdir(tmp_path)
        with (
            patch.dict(
                "sys.modules",
                {
                    "src.services.auth_service": SimpleNamespace(
                        UserRole=SimpleNamespace(
                            INSTRUCTOR=SimpleNamespace(value="instructor")
                        )
                    ),
                    "src.services.import_service": SimpleNamespace(
                        ConflictStrategy=SimpleNamespace(USE_THEIRS="use_theirs"),
                        ImportService=import_service_cls,
                    ),
                    "src.services.invitation_service": SimpleNamespace(
                        InvitationService=invitation_service
                    ),
                },
            ),
            patch.object(module.pd.DataFrame, "to_excel") as to_excel,
        ):
            module.run_generate_logs(Mock(), db)
    finally:
        module.os.chdir(original_cwd)

    invitation_service.create_invitation.assert_called_once()
    invitation_service.send_invitation.assert_called_once_with({"token": "abc"})
    to_excel.assert_called_once()
    import_service_cls.assert_called_once_with(institution_id="inst-1", verbose=True)
    import_service.import_excel_file.assert_called_once()


def test_ensure_demo_clo_paths() -> None:
    module = _load_advance_demo_module()
    db = Mock()
    db.get_course_outcomes.return_value = [{"clo_number": "1", "outcome_id": "out-1"}]

    assert module._ensure_demo_clo(db, Mock(), Mock(), "course-1", 1, "desc") == "out-1"

    db.get_course_outcomes.return_value = [{"clo_number": "1"}]
    with pytest.raises(RuntimeError):
        module._ensure_demo_clo(db, Mock(), Mock(), "course-1", 1, "desc")

    db.get_course_outcomes.return_value = []
    course_outcome_cls = Mock()
    course_outcome_cls.create_schema.return_value = {}
    clo_status = SimpleNamespace(ASSIGNED="assigned")
    db.create_course_outcome.return_value = "out-2"
    assert (
        module._ensure_demo_clo(
            db, course_outcome_cls, clo_status, "course-1", 2, "desc", "Exam"
        )
        == "out-2"
    )

    db.create_course_outcome.return_value = None
    with pytest.raises(RuntimeError):
        module._ensure_demo_clo(
            db, course_outcome_cls, clo_status, "course-1", 3, "desc"
        )


def test_get_semester_end_context_success_and_failure() -> None:
    module = _load_advance_demo_module()
    db = Mock()
    morgan = {"user_id": "m1", "institution_id": "inst-1"}
    patel = {"id": "p1", "institution_id": "inst-1"}
    admin = {"user_id": "a1", "institution_id": "inst-1"}
    biol = {"course_id": "c1", "institution_id": "inst-1"}
    zool = {"id": "c2", "institution_id": "inst-1"}
    db.get_user_by_email.side_effect = [morgan, patel, admin]
    db.get_course_by_number.side_effect = [biol, zool]

    result = module._get_semester_end_context(db)
    assert result[3:] == ("m1", "p1", "a1", biol, zool)

    db.get_user_by_email.side_effect = [None, patel, admin]
    with pytest.raises(RuntimeError):
        module._get_semester_end_context(db)


def test_create_semester_end_clos_and_status_updates() -> None:
    module = _load_advance_demo_module()
    with patch.object(
        module, "_ensure_demo_clo", side_effect=["a", "b", "c", "d", "e"]
    ) as ensure:
        assert module._create_semester_end_clos(
            Mock(), Mock(), Mock(), "biol", "zool"
        ) == (
            "a",
            "b",
            "c",
            "d",
            "e",
        )
    assert ensure.call_count == 5

    db = Mock()
    workflow = Mock()
    module._apply_semester_end_statuses(
        db,
        workflow,
        "morgan",
        "patel",
        "admin",
        "clo1",
        "clo2",
        "clo3",
        "clo4",
        "clo5",
    )
    assert db.update_outcome_assessment.call_count == 4
    workflow.submit_clo_for_approval.assert_any_call("clo1", "morgan")
    workflow.approve_clo.assert_called_once_with("clo2", "admin")
    workflow.request_rework.assert_called_once()
    workflow.mark_as_nci.assert_called_once()


def test_duplicate_course_and_reminder_paths() -> None:
    module = _load_advance_demo_module()
    db = Mock()
    biol = {"course_id": "bio-1"}
    db.get_course_by_number.return_value = {"course_id": "dup"}
    module._ensure_duplicate_course(db, "inst-1", biol)
    db.duplicate_course_record.assert_not_called()

    db.get_course_by_number.return_value = None
    db.duplicate_course_record.return_value = "dup-2"
    module._ensure_duplicate_course(db, "inst-1", biol)
    db.duplicate_course_record.assert_called_once()

    session = object()
    bulk_email_service = Mock()
    bulk_email_service.send_instructor_reminders.return_value = "job-1"
    db._db_service.sqlite.get_session.return_value = session
    with patch.object(module.time, "sleep") as sleep:
        module._trigger_semester_end_reminders(
            db, bulk_email_service, "morgan", "patel", "admin"
        )
    sleep.assert_called_once_with(2)
    bulk_email_service.send_instructor_reminders.assert_called_once_with(
        db=session,
        instructor_ids=["morgan", "patel"],
        created_by_user_id="admin",
        personal_message="Please complete your assessments by Friday.",
        term="Fall 2024",
    )

    bulk_email_service.reset_mock()
    db._db_service.sqlite.get_session.side_effect = RuntimeError("boom")
    module._trigger_semester_end_reminders(
        db, bulk_email_service, "morgan", "patel", "admin"
    )


def test_run_semester_end_and_main_dispatch(monkeypatch: Any) -> None:
    module = _load_advance_demo_module()
    db = Mock()
    biol = {"institution_id": "inst-1", "course_id": "bio-1"}
    zool = {"id": "zoo-1"}

    with (
        patch.object(
            module,
            "_get_semester_end_context",
            return_value=(
                Mock(),
                Mock(),
                Mock(),
                "morgan",
                "patel",
                "admin",
                biol,
                zool,
            ),
        ),
        patch.object(
            module, "_create_semester_end_clos", return_value=("1", "2", "3", "4", "5")
        ) as create_clos,
        patch.object(module, "_apply_semester_end_statuses") as apply_statuses,
        patch.object(module, "_ensure_duplicate_course") as ensure_duplicate,
        patch.object(module, "_trigger_semester_end_reminders") as trigger_reminders,
        patch.dict(
            "sys.modules",
            {
                "src.models.models": SimpleNamespace(CourseOutcome=Mock()),
                "src.services.bulk_email_service": SimpleNamespace(
                    BulkEmailService=Mock()
                ),
                "src.services.clo_workflow_service": SimpleNamespace(
                    CLOWorkflowService=Mock()
                ),
                "src.utils.constants": SimpleNamespace(CLOStatus=Mock()),
            },
        ),
    ):
        module.run_semester_end(Mock(), db)

    create_clos.assert_called_once()
    apply_statuses.assert_called_once()
    ensure_duplicate.assert_called_once_with(db, "inst-1", biol)
    trigger_reminders.assert_called_once()

    with patch.object(
        module, "_get_semester_end_context", side_effect=RuntimeError("bad state")
    ):
        module.run_semester_end(Mock(), db)

    app = Mock()
    app.app_context.return_value.__enter__ = Mock(return_value=None)
    app.app_context.return_value.__exit__ = Mock(return_value=None)
    fake_db_module = ModuleType("src.database.database_service")
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: argparse.Namespace(target="generate_logs", env="dev"),
    )
    with (
        patch.object(module, "setup_env") as setup_env,
        patch.object(module, "run_generate_logs") as run_generate_logs,
        patch.dict(
            "sys.modules",
            {
                "src.database.database_service": fake_db_module,
                "src.app": SimpleNamespace(app=app),
            },
        ),
    ):
        module.main()

    setup_env.assert_called_once_with("dev")
    run_generate_logs.assert_called_once()
    assert run_generate_logs.call_args.args[0] is app
