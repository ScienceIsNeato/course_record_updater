"""Unit tests for plo_service PLO trend data helpers and get_plo_trend_data.

Tests cover:
- _build_term_metadata: term status resolution
- _resolve_plo_clo_mapping: mapping → PLO↔CLO associations
- _index_outcomes_by_clo_term: section outcome indexing
- _aggregate_section_outcomes: arithmetic
- _build_trend_point: null-handling
- _extract_term_id: nested dict traversal
- _build_clo_trends / _assemble_plo_trends: assembly
- get_plo_trend_data: end-to-end with monkeypatched DB
"""

from typing import Any, Dict, List
from unittest.mock import patch

import src.database.database_service as database_service
import src.services.plo_service as plo_service
from src.services.plo_service import (
    _aggregate_section_outcomes,
    _build_clo_trends,
    _build_term_metadata,
    _build_trend_point,
    _extract_term_id,
    _index_outcomes_by_clo_term,
    get_plo_trend_data,
)

INST_DATA = {
    "name": "Trend Test U",
    "short_name": "TTU",
    "admin_email": "admin@ttu.edu",
    "created_by": "system",
}


# ---------------------------------------------------------------------------
# _build_term_metadata
# ---------------------------------------------------------------------------


class TestBuildTermMetadata:
    def test_active_term_flagged(self):
        terms = [
            {
                "id": "t1",
                "name": "Fall 2023",
                "start_date": "2023-08-01",
                "end_date": "2023-12-15",
            },
        ]
        with patch.object(plo_service, "get_term_status", return_value="ACTIVE"):
            result = _build_term_metadata(terms)
        assert len(result) == 1
        assert result[0]["term_id"] == "t1"
        assert result[0]["term_name"] == "Fall 2023"
        assert result[0]["is_current"] is True

    def test_past_term_not_current(self):
        terms = [
            {
                "id": "t2",
                "name": "Spring 2023",
                "start_date": "2023-01-10",
                "end_date": "2023-05-15",
            },
        ]
        with patch.object(plo_service, "get_term_status", return_value="PASSED"):
            result = _build_term_metadata(terms)
        assert result[0]["is_current"] is False

    def test_uses_term_id_fallback(self):
        """Falls back to term_id key when id is missing."""
        terms = [
            {"term_id": "tx", "term_name": "Test", "start_date": "", "end_date": ""}
        ]
        with patch.object(plo_service, "get_term_status", return_value="PASSED"):
            result = _build_term_metadata(terms)
        assert result[0]["term_id"] == "tx"
        assert result[0]["term_name"] == "Test"

    def test_empty_list(self):
        assert _build_term_metadata([]) == []


# ---------------------------------------------------------------------------
# _aggregate_section_outcomes
# ---------------------------------------------------------------------------


class TestAggregateSectionOutcomes:
    def test_basic_aggregation(self):
        records = [
            {"students_took": 20, "students_passed": 16},
            {"students_took": 30, "students_passed": 24},
        ]
        result = _aggregate_section_outcomes(records)
        assert result["students_took"] == 50
        assert result["students_passed"] == 40
        assert result["pass_rate"] == 80.0
        assert result["section_count"] == 2
        assert result["sections_with_data"] == 2

    def test_ignores_zero_took(self):
        records = [
            {"students_took": 10, "students_passed": 8},
            {"students_took": 0, "students_passed": 0},
        ]
        result = _aggregate_section_outcomes(records)
        assert result["students_took"] == 10
        assert result["students_passed"] == 8
        assert result["sections_with_data"] == 1
        assert result["section_count"] == 2

    def test_ignores_none_values(self):
        records = [
            {"students_took": None, "students_passed": None},
            {"students_took": 10, "students_passed": 7},
        ]
        result = _aggregate_section_outcomes(records)
        assert result["students_took"] == 10
        assert result["sections_with_data"] == 1

    def test_empty_list_returns_none_rate(self):
        result = _aggregate_section_outcomes([])
        assert result["pass_rate"] is None
        assert result["students_took"] == 0
        assert result["section_count"] == 0
        assert result["sections_with_data"] == 0


# ---------------------------------------------------------------------------
# _build_trend_point
# ---------------------------------------------------------------------------


class TestBuildTrendPoint:
    def test_returns_none_for_empty(self):
        assert _build_trend_point([], "t1") is None

    def test_returns_point_with_term_id(self):
        records = [{"students_took": 20, "students_passed": 18}]
        result = _build_trend_point(records, "t-abc")
        assert result is not None
        assert result["term_id"] == "t-abc"
        assert result["pass_rate"] == 90.0


# ---------------------------------------------------------------------------
# _extract_term_id
# ---------------------------------------------------------------------------


class TestExtractTermId:
    def test_direct_term_id(self):
        assert _extract_term_id({"term_id": "t1"}) == "t1"

    def test_nested_section_offering(self):
        so = {"_section": {"_offering": {"term_id": "t2"}}}
        assert _extract_term_id(so) == "t2"

    def test_nested_offering_flat(self):
        so = {"_offering": {"term_id": "t3"}}
        assert _extract_term_id(so) == "t3"

    def test_nested_term_object(self):
        so = {"_section": {"_offering": {"_term": {"id": "t4"}}}}
        assert _extract_term_id(so) == "t4"

    def test_section_offering_keys(self):
        so = {"section": {"offering": {"term_id": "t5"}}}
        assert _extract_term_id(so) == "t5"

    def test_returns_none_when_missing(self):
        assert _extract_term_id({}) is None
        assert _extract_term_id({"_section": {}}) is None


# ---------------------------------------------------------------------------
# _index_outcomes_by_clo_term
# ---------------------------------------------------------------------------


class TestIndexOutcomesByCloTerm:
    def test_indexes_correctly(self):
        records = [
            {"outcome_id": "c1", "term_id": "t1", "students_took": 10},
            {"outcome_id": "c1", "term_id": "t2", "students_took": 20},
            {"outcome_id": "c2", "term_id": "t1", "students_took": 30},
        ]
        idx = _index_outcomes_by_clo_term(records)
        assert len(idx["c1"]["t1"]) == 1
        assert len(idx["c1"]["t2"]) == 1
        assert len(idx["c2"]["t1"]) == 1
        assert "c2" not in idx or "t2" not in idx.get("c2", {})

    def test_multiple_sections_same_clo_term(self):
        records = [
            {"outcome_id": "c1", "term_id": "t1", "students_took": 10},
            {"outcome_id": "c1", "term_id": "t1", "students_took": 20},
        ]
        idx = _index_outcomes_by_clo_term(records)
        assert len(idx["c1"]["t1"]) == 2

    def test_skips_records_without_term_or_outcome(self):
        records = [
            {"outcome_id": "c1"},  # no term_id
            {"term_id": "t1"},  # no outcome_id
            {},  # nothing
        ]
        idx = _index_outcomes_by_clo_term(records)
        assert idx == {}

    def test_empty_input(self):
        assert _index_outcomes_by_clo_term([]) == {}


# ---------------------------------------------------------------------------
# _build_clo_trends
# ---------------------------------------------------------------------------


class TestBuildCloTrends:
    def test_produces_trend_per_clo(self):
        clo_ids = ["c1", "c2"]
        clo_meta = {
            "c1": {
                "outcome_id": "c1",
                "clo_number": "1",
                "description": "CLO 1",
                "course_number": "CS-101",
            },
            "c2": {
                "outcome_id": "c2",
                "clo_number": "2",
                "description": "CLO 2",
                "course_number": "CS-101",
            },
        }
        by_clo_term = {
            "c1": {
                "t1": [{"students_took": 20, "students_passed": 16}],
            },
        }
        term_meta = [
            {"term_id": "t1", "term_name": "Fall 2023", "is_current": False},
            {"term_id": "t2", "term_name": "Spring 2024", "is_current": False},
        ]
        result = _build_clo_trends(clo_ids, clo_meta, by_clo_term, term_meta)
        assert len(result) == 2

        # c1: has data in t1, null in t2
        c1 = result[0]
        assert c1["outcome_id"] == "c1"
        assert c1["trend"][0] is not None
        assert c1["trend"][0]["pass_rate"] == 80.0
        assert c1["trend"][1] is None

        # c2: no data anywhere
        c2 = result[1]
        assert c2["trend"][0] is None
        assert c2["trend"][1] is None


# ---------------------------------------------------------------------------
# get_plo_trend_data (integration with DB, section outcomes stubbed)
# ---------------------------------------------------------------------------


def _wire(suffix: str, num_clos: int = 2):
    """Build institution + program + 1 course + CLOs. Returns (inst_id, prog_id, [clo_ids])."""
    inst_id = database_service.create_institution(
        {**INST_DATA, "name": f"TTU {suffix}", "short_name": f"TTU{suffix}"}
    )
    prog_id = database_service.create_program(
        {
            "name": f"Program {suffix}",
            "short_name": f"P{suffix}",
            "institution_id": inst_id,
        }
    )
    course_id = database_service.create_course(
        {
            "course_number": f"TRD-{suffix}",
            "course_title": f"Trend test {suffix}",
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


def _publish(prog_id: str, entries: list) -> str:
    draft = database_service.get_or_create_plo_mapping_draft(prog_id)
    mapping_id = draft["id"]
    for plo_id, clo_id in entries:
        database_service.add_plo_mapping_entry(mapping_id, plo_id, clo_id)
    database_service.publish_plo_mapping(mapping_id, description="test")
    return mapping_id


def _make_terms(inst_id: str, count: int = 3) -> List[str]:
    """Create *count* terms and return their ids."""
    semesters = [
        ("Fall 2023", "2023-08-01", "2023-12-15"),
        ("Spring 2024", "2024-01-10", "2024-05-15"),
        ("Fall 2024", "2024-08-01", "2024-12-15"),
        ("Spring 2025", "2025-01-10", "2025-05-15"),
    ]
    term_ids = []
    for i in range(min(count, len(semesters))):
        name, start, end = semesters[i]
        tid = database_service.create_term(
            {
                "institution_id": inst_id,
                "term_name": name,
                "start_date": start,
                "end_date": end,
            }
        )
        term_ids.append(tid)
    return term_ids


def _stub_section_outcomes(
    monkeypatch,
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Patch section outcome query with canned records."""
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


class TestGetPloTrendData:
    def test_no_terms_returns_empty(self, monkeypatch):
        """No terms in institution → empty result."""
        inst_id, prog_id, _ = _wire("TRD_NT", num_clos=1)
        # No terms created → get_all_terms returns []
        result = get_plo_trend_data(prog_id, inst_id)
        assert result["terms"] == []
        assert result["plos"] == []
        assert result["mapping_version"] is None

    def test_no_mapping_returns_empty_plos(self, monkeypatch):
        """Terms exist but no published mapping → empty trends on each PLO."""
        inst_id, prog_id, _ = _wire("TRD_NM", num_clos=1)
        _make_terms(inst_id, 2)
        _make_plo(prog_id, inst_id, 1)

        # Stub so no actual query happens
        calls = _stub_section_outcomes(monkeypatch, [])

        result = get_plo_trend_data(prog_id, inst_id)
        assert len(result["terms"]) == 2
        assert len(result["plos"]) == 1
        # No mapping → no CLOs mapped → stub never called
        assert len(calls) == 0

    def test_trend_data_across_terms(self, monkeypatch):
        """Correct pass rates per term with nulls for missing terms."""
        inst_id, prog_id, clo_ids = _wire("TRD_OK", num_clos=1)
        term_ids = _make_terms(inst_id, 3)
        plo_id = _make_plo(prog_id, inst_id, 1)
        _publish(prog_id, [(plo_id, clo_ids[0])])

        # Simulate: data in term[0] and term[2], nothing in term[1]
        _stub_section_outcomes(
            monkeypatch,
            [
                {
                    "outcome_id": clo_ids[0],
                    "term_id": term_ids[0],
                    "students_took": 20,
                    "students_passed": 14,
                },
                {
                    "outcome_id": clo_ids[0],
                    "term_id": term_ids[2],
                    "students_took": 20,
                    "students_passed": 17,
                },
            ],
        )

        result = get_plo_trend_data(prog_id, inst_id)
        assert result["mapping_version"] is not None
        assert len(result["terms"]) == 3

        plo = result["plos"][0]
        assert plo["plo_number"] == 1

        # Term 0: data, Term 1: null, Term 2: data
        assert plo["trend"][0] is not None
        assert plo["trend"][0]["pass_rate"] == 70.0
        assert plo["trend"][1] is None
        assert plo["trend"][2] is not None
        assert plo["trend"][2]["pass_rate"] == 85.0

        # CLO-level same shape
        clo = plo["clos"][0]
        assert clo["trend"][0]["pass_rate"] == 70.0
        assert clo["trend"][1] is None
        assert clo["trend"][2]["pass_rate"] == 85.0

    def test_multiple_plos_independent_trends(self, monkeypatch):
        """Each PLO aggregates only its own mapped CLOs."""
        inst_id, prog_id, clo_ids = _wire("TRD_MP", num_clos=2)
        term_ids = _make_terms(inst_id, 2)
        plo1 = _make_plo(prog_id, inst_id, 1)
        plo2 = _make_plo(prog_id, inst_id, 2)
        _publish(prog_id, [(plo1, clo_ids[0]), (plo2, clo_ids[1])])

        _stub_section_outcomes(
            monkeypatch,
            [
                {
                    "outcome_id": clo_ids[0],
                    "term_id": term_ids[0],
                    "students_took": 10,
                    "students_passed": 8,
                },
                {
                    "outcome_id": clo_ids[1],
                    "term_id": term_ids[0],
                    "students_took": 10,
                    "students_passed": 5,
                },
            ],
        )

        result = get_plo_trend_data(prog_id, inst_id)
        by_num = {p["plo_number"]: p for p in result["plos"]}

        # PLO 1 → CLO 0: 80%
        assert by_num[1]["trend"][0]["pass_rate"] == 80.0
        # PLO 2 → CLO 1: 50%
        assert by_num[2]["trend"][0]["pass_rate"] == 50.0

    def test_term_ids_passed_to_query(self, monkeypatch):
        """The section-outcome query receives correct term_ids filter."""
        inst_id, prog_id, clo_ids = _wire("TRD_FI", num_clos=1)
        term_ids = _make_terms(inst_id, 2)
        plo_id = _make_plo(prog_id, inst_id, 1)
        _publish(prog_id, [(plo_id, clo_ids[0])])

        calls = _stub_section_outcomes(monkeypatch, [])
        get_plo_trend_data(prog_id, inst_id)

        assert len(calls) == 1
        assert set(calls[0]["term_ids"]) == set(term_ids)
        assert calls[0]["outcome_ids"] == [clo_ids[0]]

    def test_plo_description_fallback_to_plo(self, monkeypatch):
        """PLO description falls back to PLO record when no snapshot."""
        inst_id, prog_id, clo_ids = _wire("TRD_SN", num_clos=1)
        _make_terms(inst_id, 1)
        plo_id = _make_plo(prog_id, inst_id, 1)
        _publish(prog_id, [(plo_id, clo_ids[0])])

        _stub_section_outcomes(monkeypatch, [])
        result = get_plo_trend_data(prog_id, inst_id)

        # No snapshot → uses PLO description
        assert result["plos"][0]["description"] == "PLO 1"
