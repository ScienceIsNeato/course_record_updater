"""Focused tests for seed_db.py helper/entrypoint paths."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest


def _load_seed_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    script_path = root / "scripts" / "seed_db.py"
    spec = importlib.util.spec_from_file_location("seed_db", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_database_url_paths(monkeypatch: Any) -> None:
    module = _load_seed_module()

    args = argparse.Namespace(env="dev", clear=False, demo=False, manifest=None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://manual")
    assert module._resolve_database_url(args) == "postgresql://manual"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("NEON_DB_URL_DEV", "postgresql://dev")
    assert module._resolve_database_url(args) == "postgresql://dev"

    monkeypatch.delenv("NEON_DB_URL_DEV", raising=False)
    with pytest.raises(SystemExit) as ex:
        module._resolve_database_url(args)
    assert ex.value.code == 1

    args_local = argparse.Namespace(env="local", clear=False, demo=False, manifest=None)
    assert module._resolve_database_url(args_local) == "sqlite:///loopcloser_dev.db"


def test_confirm_deployed_environment_paths(monkeypatch: Any) -> None:
    module = _load_seed_module()

    local_args = argparse.Namespace(env="local", clear=False)
    module._confirm_deployed_environment(local_args, "sqlite:///local.db")

    remote_args = argparse.Namespace(env="dev", clear=True)
    with patch("builtins.input", return_value="yes"):
        module._confirm_deployed_environment(remote_args, "postgresql://x")

    with patch("builtins.input", return_value="no"):
        with pytest.raises(SystemExit) as ex:
            module._confirm_deployed_environment(remote_args, "postgresql://x")
        assert ex.value.code == 0

    with patch("builtins.input", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as ex2:
            module._confirm_deployed_environment(remote_args, "postgresql://x")
        assert ex2.value.code == 0


def test_clear_flask_sessions_and_rotate_token(
    tmp_path: Path, capsys: Any, monkeypatch: Any
) -> None:
    module = _load_seed_module()

    project_root = tmp_path / "proj"
    (project_root / "flask_session").mkdir(parents=True)
    (project_root / "data" / "flask_session").mkdir(parents=True)
    (project_root / "flask_session" / "a.sess").write_text("x", encoding="utf-8")
    (project_root / "data" / "flask_session" / "b.sess").write_text(
        "x", encoding="utf-8"
    )

    monkeypatch.setattr(module, "project_root", project_root)
    module._clear_flask_sessions()

    assert list((project_root / "flask_session").glob("*")) == []
    assert list((project_root / "data" / "flask_session").glob("*")) == []

    with patch(
        "src.services.auth_service.write_db_generation", return_value="abcd1234ef"
    ):
        module._rotate_db_generation()

    out = capsys.readouterr().out
    assert "Cleared 2 session file" in out
    assert "Rotated database generation token" in out


def test_execute_seeding_demo_and_baseline(tmp_path: Path, monkeypatch: Any) -> None:
    module = _load_seed_module()

    demo_args = argparse.Namespace(demo=True, clear=True, manifest=None, env="local")
    demo_instance = Mock()
    demo_instance.seed_demo.return_value = True
    demo_instance.log = Mock()

    with (
        patch.object(module, "DemoSeeder", return_value=demo_instance),
        patch("src.database.database_service.reset_database"),
        patch.object(module, "_clear_flask_sessions"),
        patch.object(module, "_rotate_db_generation"),
    ):
        assert module._execute_seeding(demo_args) is True

    baseline_args = argparse.Namespace(
        demo=False,
        clear=False,
        manifest=str(tmp_path / "manifest.json"),
        env="local",
    )
    (tmp_path / "manifest.json").write_text('{"k": "v"}', encoding="utf-8")

    baseline_instance = Mock()
    baseline_instance.seed_baseline.return_value = True
    baseline_instance.log = Mock()

    with patch.object(module, "BaselineTestSeeder", return_value=baseline_instance):
        assert module._execute_seeding(baseline_args) is True
        baseline_instance.seed_baseline.assert_called_once_with({"k": "v"})


def test_execute_seeding_manifest_load_failure(tmp_path: Path) -> None:
    module = _load_seed_module()

    args = argparse.Namespace(
        demo=False,
        clear=False,
        manifest=str(tmp_path / "missing.json"),
        env="local",
    )

    with pytest.raises(SystemExit) as ex:
        module._execute_seeding(args)
    assert ex.value.code == 1


def test_main_success_and_arg_error(monkeypatch: Any) -> None:
    module = _load_seed_module()

    # Success path
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["seed_db.py", "--env", "local"],
    )
    with (
        patch.object(module, "_resolve_database_url", return_value="sqlite:///x.db"),
        patch.object(module, "_confirm_deployed_environment"),
        patch("src.database.database_service.refresh_connection"),
        patch.object(module, "_execute_seeding", return_value=True),
    ):
        with pytest.raises(SystemExit) as ex:
            module.main()
        assert ex.value.code == 0

    # Invalid args path
    monkeypatch.setattr(module.sys, "argv", ["seed_db.py", "--bad-flag"])
    with pytest.raises(SystemExit):
        module.main()


def test_demo_story_builders_return_rich_content() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")

    payload = seeder._build_demo_narrative_payload("BIOL-101", "FA2023", "001")
    assert "narrative_celebrations" in payload
    assert "BIOL-101" in payload["narrative_celebrations"]
    assert payload["narrative_challenges"]
    assert payload["narrative_changes"]

    feedback = seeder._build_demo_feedback_comment("BIOL-101", "SP2025", "1", 22, 25)
    assert "BIOL-101 CLO 1" in feedback
    assert "88% pass rate" in feedback

    zero_feedback = seeder._build_demo_feedback_comment("BIOL-101", "SP2025", "1", 0, 0)
    assert "0% pass rate" in zero_feedback


def test_backfill_demo_story_data_updates_missing_narratives_and_feedback() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder._resolve_section_id = Mock(return_value="section-1")
    seeder._find_section_outcome = Mock(return_value={"id": "outcome-1"})

    manifest = {
        "section_outcome_overrides": [
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 1,
                "students_took": 25,
                "students_passed": 22,
            }
        ],
        "section_narrative_overrides": [],
        "section_feedback_overrides": [],
    }

    with (
        patch.object(
            module.database_service.db, "update_course_section", return_value=True
        ) as update_section,
        patch.object(
            module.database_service.db, "update_section_outcome", return_value=True
        ) as update_outcome,
    ):
        stats = seeder._backfill_demo_story_data(
            manifest, "inst-1", {"FA2023": "term-1"}
        )

    assert stats == {"narratives": 1, "feedback": 1}
    update_section.assert_called_once()
    update_outcome.assert_called_once()
    assert "feedback_comments" in update_outcome.call_args.args[1]


def test_apply_demo_enrichments_runs_all_optional_paths() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder.log = Mock()

    manifest = {
        "section_outcome_overrides": [{"course_code": "BIOL-101"}],
        "section_narrative_overrides": [{"course_code": "BIOL-101"}],
        "section_feedback_overrides": [{"course_code": "BIOL-101"}],
        "program_outcomes": {"BIOL": {"plos": []}},
    }

    with (
        patch.object(seeder, "apply_section_outcome_overrides", return_value=4) as clo,
        patch.object(
            seeder, "_apply_section_narrative_overrides", return_value=2
        ) as narr,
        patch.object(
            seeder, "_apply_section_feedback_overrides", return_value=3
        ) as feedback,
        patch.object(
            seeder,
            "_backfill_demo_story_data",
            return_value={"narratives": 5, "feedback": 6},
        ) as backfill,
        patch.object(
            seeder,
            "_create_plos_from_manifest",
            return_value={"plo_count": 7, "entry_count": 8, "published_count": 1},
        ) as plos,
    ):
        seeder._apply_demo_enrichments(manifest, "inst-1", {"FA2023": "term-1"}, {})

    clo.assert_called_once()
    narr.assert_called_once()
    feedback.assert_called_once()
    backfill.assert_called_once()
    plos.assert_called_once()


def test_apply_demo_enrichments_skips_backfill_without_outcome_overrides() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder.log = Mock()

    manifest = {
        "section_narrative_overrides": [{"course_code": "BIOL-101"}],
        "section_feedback_overrides": [{"course_code": "BIOL-101"}],
    }

    with (
        patch.object(
            seeder, "_apply_section_narrative_overrides", return_value=2
        ) as narr,
        patch.object(
            seeder, "_apply_section_feedback_overrides", return_value=3
        ) as feedback,
        patch.object(seeder, "_backfill_demo_story_data") as backfill,
    ):
        seeder._apply_demo_enrichments(manifest, "inst-1", {"FA2023": "term-1"}, {})

    narr.assert_called_once()
    feedback.assert_called_once()
    backfill.assert_not_called()


def test_apply_section_narrative_overrides_covers_skip_and_success_paths() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder.log = Mock()
    seeder._resolve_section_id = Mock(side_effect=[None, "section-2", "section-3"])

    overrides = [
        {"_comment": "skip me"},
        {"course_code": None, "section_number": "001"},
        {
            "course_code": "BIOL-101",
            "section_number": "001",
            "term_code": "FA2023",
            "narrative_celebrations": "Nice work",
        },
        {
            "course_code": "BIOL-101",
            "section_number": "002",
            "term_code": "FA2023",
        },
        {
            "course_code": "BIOL-101",
            "section_number": "003",
            "term_code": "FA2023",
            "narrative_changes": "Add more scaffolding",
        },
    ]

    with patch.object(
        module.database_service.db, "update_course_section", return_value=True
    ) as update_section:
        applied = seeder._apply_section_narrative_overrides(
            overrides, "inst-1", {"FA2023": "term-1"}
        )

    assert applied == 1
    update_section.assert_called_once_with(
        "section-3", {"narrative_changes": "Add more scaffolding"}
    )
    assert seeder.log.call_count == 1


def test_apply_section_narrative_overrides_keeps_real_entries_with_comments() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder.log = Mock()
    seeder._resolve_section_id = Mock(return_value="section-1")

    overrides = [
        {
            "_comment": "context for this seeded example",
            "course_code": "BIOL-101",
            "section_number": "001",
            "term_code": "FA2023",
            "narrative_changes": "Keep the explanatory note and still apply",
        }
    ]

    with patch.object(
        module.database_service.db, "update_course_section", return_value=True
    ) as update_section:
        applied = seeder._apply_section_narrative_overrides(
            overrides, "inst-1", {"FA2023": "term-1"}
        )

    assert applied == 1
    update_section.assert_called_once_with(
        "section-1",
        {"narrative_changes": "Keep the explanatory note and still apply"},
    )


def test_apply_section_feedback_overrides_covers_skip_and_success_paths() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder.log = Mock()
    seeder._find_section_outcome = Mock(side_effect=[None, {"id": "outcome-2"}])

    overrides = [
        {"_comment": "skip me"},
        {
            "course_code": "BIOL-101",
            "section_number": "001",
            "clo_number": 1,
            "feedback_comments": None,
        },
        {
            "course_code": "BIOL-101",
            "section_number": "001",
            "term_code": "FA2023",
            "feedback_comments": "Missing clo number",
        },
        {
            "course_code": "BIOL-101",
            "section_number": "001",
            "clo_number": 1,
            "term_code": "FA2023",
            "feedback_comments": "Needs follow-up",
        },
        {
            "course_code": "BIOL-101",
            "section_number": "002",
            "clo_number": 2,
            "term_code": "FA2023",
            "feedback_comments": "Looks good",
        },
    ]

    with patch.object(
        module.database_service.db, "update_section_outcome", return_value=True
    ) as update_outcome:
        applied = seeder._apply_section_feedback_overrides(
            overrides, "inst-1", {"FA2023": "term-1"}
        )

    assert applied == 1
    update_outcome.assert_called_once_with(
        "outcome-2", {"feedback_comments": "Looks good"}
    )
    assert seeder.log.call_count == 1


def test_backfill_demo_story_data_skips_explicit_missing_and_unassessed_entries() -> (
    None
):
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder._resolve_section_id = Mock(return_value=None)
    seeder._find_section_outcome = Mock(return_value=None)

    manifest = {
        "section_outcome_overrides": [
            {"_comment": "skip me"},
            {"course_code": None, "section_number": "001", "students_took": 12},
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 1,
                "students_took": 0,
            },
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 1,
                "students_took": 25,
                "students_passed": 22,
            },
        ],
        "section_narrative_overrides": [
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "narrative_changes": "Already explicit",
            }
        ],
        "section_feedback_overrides": [
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "feedback_comments": "Missing clo number should not register",
            },
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 1,
                "feedback_comments": "Already explicit",
            },
        ],
    }

    with (
        patch.object(
            module.database_service.db, "update_course_section"
        ) as update_section,
        patch.object(
            module.database_service.db, "update_section_outcome"
        ) as update_outcome,
    ):
        stats = seeder._backfill_demo_story_data(
            manifest, "inst-1", {"FA2023": "term-1"}
        )

    assert stats == {"narratives": 0, "feedback": 0}
    update_section.assert_not_called()
    update_outcome.assert_not_called()


def test_backfill_demo_story_data_caches_missing_section_resolution() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder._resolve_section_id = Mock(return_value=None)
    seeder._find_section_outcome = Mock(return_value=None)

    manifest = {
        "section_outcome_overrides": [
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 1,
                "students_took": 25,
                "students_passed": 22,
            },
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 2,
                "students_took": 24,
                "students_passed": 20,
            },
        ],
    }

    stats = seeder._backfill_demo_story_data(manifest, "inst-1", {"FA2023": "term-1"})

    assert stats == {"narratives": 0, "feedback": 0}
    seeder._resolve_section_id.assert_called_once_with(
        "BIOL-101", "001", "inst-1", "term-1"
    )


def test_backfill_demo_story_data_handles_zero_student_sections() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder._resolve_section_id = Mock(return_value="section-1")
    seeder._find_section_outcome = Mock(return_value={"id": "outcome-1"})

    manifest = {
        "section_outcome_overrides": [
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 1,
                "students_took": 0,
                "students_passed": 0,
            }
        ]
    }

    with (
        patch.object(
            module.database_service.db, "update_course_section", return_value=True
        ) as update_section,
        patch.object(
            module.database_service.db, "update_section_outcome", return_value=True
        ) as update_outcome,
    ):
        stats = seeder._backfill_demo_story_data(
            manifest, "inst-1", {"FA2023": "term-1"}
        )

    assert stats == {"narratives": 1, "feedback": 1}
    update_section.assert_called_once()
    update_outcome.assert_called_once()
    assert (
        "BIOL-101 CLO 1 is sitting at 0% pass rate"
        in update_outcome.call_args.args[1]["feedback_comments"]
    )


def test_backfill_demo_story_data_ignores_incomplete_explicit_override_keys() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder._resolve_section_id = Mock(return_value="section-1")
    seeder._find_section_outcome = Mock(return_value={"id": "outcome-1"})

    manifest = {
        "section_outcome_overrides": [
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 1,
                "students_took": 25,
                "students_passed": 22,
            }
        ],
        "section_narrative_overrides": [
            {"_comment": "context", "course_code": "BIOL-101"}
        ],
        "section_feedback_overrides": [
            {
                "_comment": "context",
                "course_code": "BIOL-101",
                "clo_number": 1,
            }
        ],
    }

    with (
        patch.object(
            module.database_service.db, "update_course_section", return_value=True
        ) as update_section,
        patch.object(
            module.database_service.db, "update_section_outcome", return_value=True
        ) as update_outcome,
    ):
        stats = seeder._backfill_demo_story_data(
            manifest, "inst-1", {"FA2023": "term-1"}
        )

    assert stats == {"narratives": 1, "feedback": 1}
    update_section.assert_called_once()
    update_outcome.assert_called_once()


def test_backfill_demo_story_data_does_not_retry_failed_narrative_updates() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")
    seeder._resolve_section_id = Mock(return_value="section-1")
    seeder._find_section_outcome = Mock(return_value=None)

    manifest = {
        "section_outcome_overrides": [
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 1,
                "students_took": 25,
                "students_passed": 22,
            },
            {
                "course_code": "BIOL-101",
                "section_number": "001",
                "term_code": "FA2023",
                "clo_number": 2,
                "students_took": 24,
                "students_passed": 20,
            },
        ],
    }

    with patch.object(
        module.database_service.db, "update_course_section", return_value=False
    ) as update_section:
        stats = seeder._backfill_demo_story_data(
            manifest, "inst-1", {"FA2023": "term-1"}
        )

    assert stats == {"narratives": 0, "feedback": 0}
    update_section.assert_called_once()


def test_resolve_section_id_handles_missing_course_and_missing_course_id() -> None:
    module = _load_seed_module()
    seeder = module.DemoSeeder(env="local")

    with patch.object(
        module.database_service.db,
        "get_course_by_number",
        side_effect=[None, {"course_id": None}, {"id": "course-3"}],
    ):
        assert seeder._resolve_section_id("BIOL-101", "001", "inst-1") is None
        assert seeder._resolve_section_id("BIOL-101", "001", "inst-1") is None
        with patch.object(
            seeder, "_find_section_id", return_value="section-9"
        ) as find_section:
            assert (
                seeder._resolve_section_id("BIOL-101", "001", "inst-1", "term-1")
                == "section-9"
            )
            find_section.assert_called_once_with("course-3", "001", "term-1")
