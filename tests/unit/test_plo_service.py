"""Unit tests for plo_service.get_plo_dashboard_tree aggregation logic.

These tests exercise the *computation* inside the tree builder
(PLO/CLO aggregation, pass-rate arithmetic, section-count tallies) by
stubbing ``get_section_outcomes_by_criteria`` with controlled payloads.
Real DB calls handle PLO/mapping/CLO creation so the mapping-resolution
path stays under test; only the section-outcome join is faked because
building the full term → offering → section → section_outcome chain
per test is disproportionately heavy.

Route-level HTTP contract tests live in test_plo_routes.py.
"""

from typing import Any, Dict, List

import pytest

import src.database.database_service as database_service
import src.services.plo_service as plo_service
from src.services.plo_service import get_plo_dashboard_tree

INST_DATA = {
    "name": "PLO Service Test U",
    "short_name": "PSTU",
    "admin_email": "admin@pstu.edu",
    "created_by": "system",
}


def _wire(suffix: str, num_clos: int = 2):
    """Build institution + program + 1 course (linked) + *num_clos* CLOs.

    Returns (inst_id, prog_id, [clo_id, ...]).
    """
    inst_id = database_service.create_institution(
        {**INST_DATA, "name": f"PSTU {suffix}", "short_name": f"PSTU{suffix}"}
    )
    prog_id = database_service.create_program(
        {
            "name": f"Program {suffix}",
            "short_name": f"PROG{suffix}",
            "institution_id": inst_id,
        }
    )
    course_id = database_service.create_course(
        {
            "course_number": f"SVC-{suffix}",
            "course_title": f"Service test course {suffix}",
            "department": "TEST",
            "institution_id": inst_id,
        }
    )
    database_service.add_course_to_program(course_id, prog_id)
    clo_ids: List[str] = []
    for i in range(num_clos):
        clo_ids.append(
            database_service.create_course_outcome(
                {
                    "course_id": course_id,
                    "clo_number": i + 1,
                    "description": f"CLO {i+1} for {suffix}",
                    "assessment_method": "exam",
                    "active": True,
                }
            )
        )
    return inst_id, prog_id, clo_ids


def _make_plo(prog_id: str, inst_id: str, n: int) -> str:
    return database_service.create_program_outcome(
        {
            "program_id": prog_id,
            "institution_id": inst_id,
            "plo_number": n,
            "description": f"PLO {n}",
        }
    )


def _publish(prog_id: str, entries: List[tuple]) -> str:
    """Publish a mapping with *entries* [(plo_id, clo_id), ...]."""
    draft = database_service.get_or_create_plo_mapping_draft(prog_id)
    mapping_id = draft["id"]
    for plo_id, clo_id in entries:
        database_service.add_plo_mapping_entry(mapping_id, plo_id, clo_id)
    database_service.publish_plo_mapping(mapping_id, description="test")
    return mapping_id


def _fake_sections(monkeypatch, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Replace the section-outcome query with a canned list.

    Each record needs at minimum: outcome_id, students_took,
    students_passed. The tree builder ignores everything else for
    aggregation purposes.

    Patches the name as looked up *inside plo_service* (the module
    does ``from src.database import database_service`` then
    ``database_service.get_section_outcomes_by_criteria(...)``).
    """
    captured: List[Dict[str, Any]] = []

    def _stub(**kw: Any) -> List[Dict[str, Any]]:
        captured.append(dict(kw))
        return records

    monkeypatch.setattr(
        plo_service.database_service,
        "get_section_outcomes_by_criteria",
        _stub,
    )
    return captured


# ---------------------------------------------------------------------------
# Aggregation arithmetic
# ---------------------------------------------------------------------------


class TestAggregation:
    def test_plo_aggregate_sums_across_clos_and_sections(self, monkeypatch):
        """PLO aggregate = sum of students_took/passed across all its CLOs' sections."""
        inst_id, prog_id, clo_ids = _wire("AGG1", num_clos=2)
        plo_id = _make_plo(prog_id, inst_id, 1)
        _publish(prog_id, [(plo_id, clo_ids[0]), (plo_id, clo_ids[1])])

        _fake_sections(
            monkeypatch,
            [
                # CLO[0] — two sections: 30→24 and 20→10
                {"outcome_id": clo_ids[0], "students_took": 30, "students_passed": 24},
                {"outcome_id": clo_ids[0], "students_took": 20, "students_passed": 10},
                # CLO[1] — one section: 10→9
                {"outcome_id": clo_ids[1], "students_took": 10, "students_passed": 9},
            ],
        )

        tree = get_plo_dashboard_tree(prog_id, inst_id)
        plo = tree["plos"][0]

        # PLO-level: 30+20+10 = 60 took, 24+10+9 = 43 passed
        assert plo["aggregate"]["students_took"] == 60
        assert plo["aggregate"]["students_passed"] == 43
        assert plo["aggregate"]["pass_rate"] == pytest.approx(71.7, abs=0.1)
        assert plo["aggregate"]["section_count"] == 3
        assert plo["aggregate"]["sections_with_data"] == 3

        # CLO-level aggregates are independent
        clo_by_id = {c["outcome_id"]: c for c in plo["clos"]}
        agg0 = clo_by_id[clo_ids[0]]["aggregate"]
        assert agg0["students_took"] == 50
        assert agg0["students_passed"] == 34
        assert agg0["pass_rate"] == 68.0
        assert agg0["section_count"] == 2

        agg1 = clo_by_id[clo_ids[1]]["aggregate"]
        assert agg1["students_took"] == 10
        assert agg1["pass_rate"] == 90.0
        assert agg1["section_count"] == 1

    def test_sections_without_data_excluded_from_rate(self, monkeypatch):
        """students_took=0 / None / non-int rows count in section_count only."""
        inst_id, prog_id, clo_ids = _wire("AGG2", num_clos=1)
        plo_id = _make_plo(prog_id, inst_id, 1)
        _publish(prog_id, [(plo_id, clo_ids[0])])

        _fake_sections(
            monkeypatch,
            [
                {"outcome_id": clo_ids[0], "students_took": 20, "students_passed": 15},
                # Zero-took — shouldn't contribute to rate
                {"outcome_id": clo_ids[0], "students_took": 0, "students_passed": 0},
                # None — ignored
                {
                    "outcome_id": clo_ids[0],
                    "students_took": None,
                    "students_passed": None,
                },
                # Missing passed — ignored (isinstance(None, int) is False)
                {"outcome_id": clo_ids[0], "students_took": 5, "students_passed": None},
            ],
        )

        tree = get_plo_dashboard_tree(prog_id, inst_id)
        agg = tree["plos"][0]["aggregate"]

        assert agg["students_took"] == 20  # only the first row
        assert agg["students_passed"] == 15
        assert agg["pass_rate"] == 75.0
        assert agg["section_count"] == 4  # all rows present
        assert agg["sections_with_data"] == 1  # only the first row counted

    def test_empty_sections_yields_none_pass_rate(self, monkeypatch):
        """No section outcomes → pass_rate=None, zero counts."""
        inst_id, prog_id, clo_ids = _wire("AGG3", num_clos=1)
        plo_id = _make_plo(prog_id, inst_id, 1)
        _publish(prog_id, [(plo_id, clo_ids[0])])

        _fake_sections(monkeypatch, [])

        tree = get_plo_dashboard_tree(prog_id, inst_id)
        agg = tree["plos"][0]["aggregate"]
        assert agg["pass_rate"] is None
        assert agg["students_took"] == 0
        assert agg["section_count"] == 0

    def test_sections_attached_to_correct_clo(self, monkeypatch):
        """Records are indexed by outcome_id — no cross-CLO leakage."""
        inst_id, prog_id, clo_ids = _wire("AGG4", num_clos=2)
        plo_id = _make_plo(prog_id, inst_id, 1)
        _publish(prog_id, [(plo_id, clo_ids[0]), (plo_id, clo_ids[1])])

        s0 = {"outcome_id": clo_ids[0], "students_took": 10, "students_passed": 7}
        s1 = {"outcome_id": clo_ids[1], "students_took": 99, "students_passed": 1}
        _fake_sections(monkeypatch, [s0, s1])

        tree = get_plo_dashboard_tree(prog_id, inst_id)
        clo_by_id = {c["outcome_id"]: c for c in tree["plos"][0]["clos"]}
        assert clo_by_id[clo_ids[0]]["sections"] == [s0]
        assert clo_by_id[clo_ids[1]]["sections"] == [s1]

    def test_unmapped_clo_sections_ignored(self, monkeypatch):
        """Section outcomes for a CLO NOT in the mapping don't bleed into the tree."""
        inst_id, prog_id, clo_ids = _wire("AGG5", num_clos=2)
        plo_id = _make_plo(prog_id, inst_id, 1)
        # Only map CLO[0] — CLO[1] is an orphan
        _publish(prog_id, [(plo_id, clo_ids[0])])

        # Feed back a section outcome for the ORPHAN CLO[1] too
        _fake_sections(
            monkeypatch,
            [
                {"outcome_id": clo_ids[0], "students_took": 10, "students_passed": 8},
                {"outcome_id": clo_ids[1], "students_took": 999, "students_passed": 1},
            ],
        )

        tree = get_plo_dashboard_tree(prog_id, inst_id)
        plo = tree["plos"][0]
        # Orphan CLO not in the tree and its 999 not in the aggregate
        assert plo["clo_count"] == 1
        assert plo["aggregate"]["students_took"] == 10


# ---------------------------------------------------------------------------
# Mapping resolution + filtering passthrough
# ---------------------------------------------------------------------------


class TestMappingResolution:
    def test_no_mapping_means_no_section_fetch(self, monkeypatch):
        """With no mapping at all, the section-outcome query is never called."""
        inst_id, prog_id, _ = _wire("MR1", num_clos=1)
        _make_plo(prog_id, inst_id, 1)
        # No draft, no publish

        calls = _fake_sections(monkeypatch, [])
        tree = get_plo_dashboard_tree(prog_id, inst_id)
        assert tree["mapping_status"] == "none"
        assert calls == []  # never called — all_clo_ids is empty

    def test_outcome_ids_filter_passed_to_query(self, monkeypatch):
        """Only mapped CLO ids land in the outcome_ids filter."""
        inst_id, prog_id, clo_ids = _wire("MR2", num_clos=3)
        plo_id = _make_plo(prog_id, inst_id, 1)
        # Map only two of the three CLOs
        _publish(prog_id, [(plo_id, clo_ids[0]), (plo_id, clo_ids[2])])

        calls = _fake_sections(monkeypatch, [])
        get_plo_dashboard_tree(prog_id, inst_id)
        assert len(calls) == 1
        assert set(calls[0]["outcome_ids"]) == {clo_ids[0], clo_ids[2]}
        assert calls[0]["institution_id"] == inst_id
        assert calls[0]["program_id"] == prog_id
        assert calls[0]["term_id"] is None

    def test_term_id_forwarded(self, monkeypatch):
        """term_id param is passed through to the section query."""
        inst_id, prog_id, clo_ids = _wire("MR3", num_clos=1)
        plo_id = _make_plo(prog_id, inst_id, 1)
        _publish(prog_id, [(plo_id, clo_ids[0])])

        calls = _fake_sections(monkeypatch, [])
        result = get_plo_dashboard_tree(prog_id, inst_id, term_id="t-xyz")
        assert result["term_id"] == "t-xyz"
        assert calls[0]["term_id"] == "t-xyz"

    def test_multiple_plos_each_get_own_clos(self, monkeypatch):
        """Entries are partitioned correctly when multiple PLOs share the mapping."""
        inst_id, prog_id, clo_ids = _wire("MR4", num_clos=3)
        plo1 = _make_plo(prog_id, inst_id, 1)
        plo2 = _make_plo(prog_id, inst_id, 2)
        # PLO-1 owns CLO[0,1]; PLO-2 owns CLO[2]
        _publish(
            prog_id,
            [(plo1, clo_ids[0]), (plo1, clo_ids[1]), (plo2, clo_ids[2])],
        )

        _fake_sections(monkeypatch, [])
        tree = get_plo_dashboard_tree(prog_id, inst_id)

        by_id = {p["id"]: p for p in tree["plos"]}
        clos1 = {c["outcome_id"] for c in by_id[plo1]["clos"]}
        clos2 = {c["outcome_id"] for c in by_id[plo2]["clos"]}
        assert clos1 == {clo_ids[0], clo_ids[1]}
        assert clos2 == {clo_ids[2]}


# ---------------------------------------------------------------------------
# Display mode lookup
# ---------------------------------------------------------------------------


class TestDisplayMode:
    def test_default_is_both(self):
        inst_id, prog_id, _ = _wire("DM1", num_clos=0)
        tree = get_plo_dashboard_tree(prog_id, inst_id)
        assert tree["assessment_display_mode"] == "both"

    def test_reads_from_program_extras(self):
        inst_id, prog_id, _ = _wire("DM2", num_clos=0)
        database_service.update_program(prog_id, {"assessment_display_mode": "binary"})
        tree = get_plo_dashboard_tree(prog_id, inst_id)
        assert tree["assessment_display_mode"] == "binary"

    def test_unknown_program_falls_back_to_both(self):
        """If program lookup fails (shouldn't happen via the route), default to 'both'."""
        # Use a real institution so the tree builder has a valid inst_id
        # but a garbage program_id that doesn't exist.
        inst_id = database_service.create_institution(
            {**INST_DATA, "name": "DM3 Inst", "short_name": "DM3"}
        )
        tree = get_plo_dashboard_tree("garbage-program-id", inst_id)
        assert tree["assessment_display_mode"] == "both"
        assert tree["mapping_status"] == "none"
        assert tree["plos"] == []
