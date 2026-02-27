"""Unit tests for src.services.plo_dashboard_service."""

from unittest.mock import patch

from src.services.plo_dashboard_service import (
    DEFAULT_DISPLAY_MODE,
    DISPLAY_BINARY,
    DISPLAY_BOTH,
    DISPLAY_PERCENTAGE,
    get_assessment_display_mode,
    get_plo_dashboard_tree,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INST_ID = "inst-1"
_TERM_ID = "term-1"
_PROG_ID = "prog-1"

_PROGRAM = {
    "id": _PROG_ID,
    "name": "Biology",
    "short_name": "BIOL",
    "extras": {},
}

_TERM = {"id": _TERM_ID, "name": "Fall 2025"}

_PLO_1 = {"id": "plo-1", "plo_number": 1, "description": "Scientific reasoning"}
_PLO_2 = {"id": "plo-2", "plo_number": 2, "description": "Lab proficiency"}

_COURSE = {"id": "course-1", "course_number": "BIOL-101", "name": "Intro Biology"}

_CLO = {
    "id": "clo-1",
    "clo_number": 1,
    "description": "Explain scientific method",
    "course_id": "course-1",
    "status": "submitted",
    "assessment_method": "exam",
}

_MAPPING = {
    "id": "map-1",
    "version": 1,
    "status": "published",
    "entries": [
        {
            "id": "entry-1",
            "program_outcome_id": "plo-1",
            "course_outcome_id": "clo-1",
        },
    ],
}

_SECTION_OUTCOME = {
    "id": "so-1",
    "outcome_id": "clo-1",
    "students_took": 30,
    "students_passed": 25,
    "assessment_tool": "Midterm Exam",
    "status": "submitted",
    "section": {
        "id": "sec-1",
        "section_number": "001",
        "instructor": {
            "first_name": "Jane",
            "last_name": "Doe",
        },
    },
}


# ---------------------------------------------------------------------------
# get_assessment_display_mode
# ---------------------------------------------------------------------------


class TestGetAssessmentDisplayMode:
    def test_default_when_no_extras(self):
        assert get_assessment_display_mode({}) == DEFAULT_DISPLAY_MODE

    def test_default_when_extras_none(self):
        assert get_assessment_display_mode({"extras": None}) == DEFAULT_DISPLAY_MODE

    def test_returns_percentage(self):
        prog = {"extras": {"plo_assessment_display": DISPLAY_PERCENTAGE}}
        assert get_assessment_display_mode(prog) == DISPLAY_PERCENTAGE

    def test_returns_binary(self):
        prog = {"extras": {"plo_assessment_display": DISPLAY_BINARY}}
        assert get_assessment_display_mode(prog) == DISPLAY_BINARY

    def test_returns_both(self):
        prog = {"extras": {"plo_assessment_display": DISPLAY_BOTH}}
        assert get_assessment_display_mode(prog) == DISPLAY_BOTH

    def test_invalid_value_falls_back(self):
        prog = {"extras": {"plo_assessment_display": "invalid"}}
        assert get_assessment_display_mode(prog) == DEFAULT_DISPLAY_MODE


# ---------------------------------------------------------------------------
# get_plo_dashboard_tree — basic structure
# ---------------------------------------------------------------------------


_BASE = "src.services.plo_dashboard_service.database_service"


class TestGetPloDashboardTreeEmpty:
    """Tests with minimal / empty data."""

    @patch(f"{_BASE}.get_programs_by_institution")
    def test_no_programs(self, mock_programs):
        mock_programs.return_value = []
        result = get_plo_dashboard_tree(_INST_ID)

        assert result["programs"] == []
        assert result["term"] is None
        assert result["summary"]["total_programs"] == 0
        assert result["summary"]["total_plos"] == 0

    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_program_without_plos(
        self, mock_programs, mock_plos, mock_mapping, mock_courses, mock_clos
    ):
        mock_programs.return_value = [_PROGRAM]
        mock_plos.return_value = []
        mock_mapping.return_value = None
        mock_courses.return_value = []
        mock_clos.return_value = []

        result = get_plo_dashboard_tree(_INST_ID)

        assert len(result["programs"]) == 1
        p = result["programs"][0]
        assert p["plo_count"] == 0
        assert p["plos"] == []
        assert p["mapping_version"] is None

    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_plos_without_mapping(
        self, mock_programs, mock_plos, mock_mapping, mock_courses, mock_clos
    ):
        mock_programs.return_value = [_PROGRAM]
        mock_plos.return_value = [_PLO_1, _PLO_2]
        mock_mapping.return_value = None
        mock_courses.return_value = []
        mock_clos.return_value = []

        result = get_plo_dashboard_tree(_INST_ID)

        p = result["programs"][0]
        assert p["plo_count"] == 2
        assert p["mapped_clo_count"] == 0
        assert all(plo["mapped_clo_count"] == 0 for plo in p["plos"])


# ---------------------------------------------------------------------------
# get_plo_dashboard_tree — with data
# ---------------------------------------------------------------------------


def _setup_full_tree_mocks(
    mock_programs, mock_term, mock_plos, mock_mapping, mock_courses, mock_clos, mock_so
):
    """Set up mocks for full tree tests and return the result."""
    mock_programs.return_value = [_PROGRAM]
    mock_term.return_value = _TERM
    mock_plos.return_value = [_PLO_1]
    mock_mapping.return_value = _MAPPING
    mock_courses.return_value = [_COURSE]
    mock_clos.return_value = [_CLO]
    mock_so.return_value = [_SECTION_OUTCOME]
    return get_plo_dashboard_tree(_INST_ID, term_id=_TERM_ID)


class TestGetPloDashboardTreeWithData:
    """Tests with PLOs, mappings, CLOs, and section outcomes."""

    @patch(f"{_BASE}.get_section_outcomes_by_criteria")
    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_term_by_id")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_full_tree_summary(self, *mocks):
        result = _setup_full_tree_mocks(*mocks)
        assert result["term"]["id"] == _TERM_ID
        assert result["term"]["name"] == "Fall 2025"
        s = result["summary"]
        assert s["total_programs"] == 1
        assert s["total_plos"] == 1
        assert s["total_mapped_clos"] == 1
        assert s["clos_with_data"] == 1
        assert s["clos_missing_data"] == 0

    @patch(f"{_BASE}.get_section_outcomes_by_criteria")
    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_term_by_id")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_full_tree_program_node(self, *mocks):
        result = _setup_full_tree_mocks(*mocks)
        p = result["programs"][0]
        assert p["id"] == _PROG_ID
        assert p["name"] == "Biology"
        assert p["plo_count"] == 1
        assert p["mapping_version"] == 1
        assert p["assessment_display_mode"] == DISPLAY_PERCENTAGE

    @patch(f"{_BASE}.get_section_outcomes_by_criteria")
    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_term_by_id")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_full_tree_clo_and_sections(self, *mocks):
        result = _setup_full_tree_mocks(*mocks)
        clo = result["programs"][0]["plos"][0]["mapped_clos"][0]
        assert clo["clo_number"] == 1
        assert clo["course_code"] == "BIOL-101"
        assert clo["students_took"] == 30
        assert clo["students_passed"] == 25
        sec = clo["sections"][0]
        assert sec["section_number"] == "001"
        assert sec["instructor_name"] == "Jane Doe"

    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_clo_without_assessment_data(
        self, mock_programs, mock_plos, mock_mapping, mock_courses, mock_clos
    ):
        """CLO with no section outcomes should count as missing data."""
        mock_programs.return_value = [_PROGRAM]
        mock_plos.return_value = [_PLO_1]
        mock_mapping.return_value = _MAPPING
        mock_courses.return_value = [_COURSE]
        mock_clos.return_value = [_CLO]

        result = get_plo_dashboard_tree(_INST_ID)

        s = result["summary"]
        assert s["clos_with_data"] == 0
        assert s["clos_missing_data"] == 1

        clo = result["programs"][0]["plos"][0]["mapped_clos"][0]
        assert clo["students_took"] is None
        assert clo["students_passed"] is None

    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_assessment_display_mode_propagates(
        self, mock_programs, mock_plos, mock_mapping, mock_courses, mock_clos
    ):
        prog_both = {**_PROGRAM, "extras": {"plo_assessment_display": "both"}}
        mock_programs.return_value = [prog_both]
        mock_plos.return_value = []
        mock_mapping.return_value = None
        mock_courses.return_value = []
        mock_clos.return_value = []

        result = get_plo_dashboard_tree(_INST_ID)
        assert result["programs"][0]["assessment_display_mode"] == DISPLAY_BOTH


# ---------------------------------------------------------------------------
# get_plo_dashboard_tree — filtering
# ---------------------------------------------------------------------------


class TestGetPloDashboardTreeFilters:
    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_program_filter(
        self, mock_programs, mock_plos, mock_mapping, mock_courses, mock_clos
    ):
        prog2 = {**_PROGRAM, "id": "prog-2", "name": "Zoology", "short_name": "ZOOL"}
        mock_programs.return_value = [_PROGRAM, prog2]
        mock_plos.return_value = []
        mock_mapping.return_value = None
        mock_courses.return_value = []
        mock_clos.return_value = []

        result = get_plo_dashboard_tree(_INST_ID, program_id="prog-2")

        assert len(result["programs"]) == 1
        assert result["programs"][0]["id"] == "prog-2"

    @patch(f"{_BASE}.get_section_outcomes_by_criteria")
    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_term_by_id")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_term_filter_passes_to_section_outcomes(
        self,
        mock_programs,
        mock_term,
        mock_plos,
        mock_mapping,
        mock_courses,
        mock_clos,
        mock_so,
    ):
        mock_programs.return_value = [_PROGRAM]
        mock_term.return_value = _TERM
        mock_plos.return_value = []
        mock_mapping.return_value = None
        mock_courses.return_value = []
        mock_clos.return_value = []
        mock_so.return_value = []

        get_plo_dashboard_tree(_INST_ID, term_id=_TERM_ID)

        mock_so.assert_called_once_with(institution_id=_INST_ID, term_id=_TERM_ID)

    @patch(f"{_BASE}.get_term_by_id")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_invalid_term_id(self, mock_programs, mock_term):
        mock_programs.return_value = []
        mock_term.return_value = None

        result = get_plo_dashboard_tree(_INST_ID, term_id="nonexistent")
        assert result["term"] is None


# ---------------------------------------------------------------------------
# get_plo_dashboard_tree — section aggregation
# ---------------------------------------------------------------------------


class TestSectionAggregation:
    @patch(f"{_BASE}.get_section_outcomes_by_criteria")
    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_term_by_id")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_multiple_sections_aggregated(
        self,
        mock_programs,
        mock_term,
        mock_plos,
        mock_mapping,
        mock_courses,
        mock_clos,
        mock_so,
    ):
        so_1 = {
            **_SECTION_OUTCOME,
            "id": "so-1",
            "students_took": 20,
            "students_passed": 18,
        }
        so_2 = {
            **_SECTION_OUTCOME,
            "id": "so-2",
            "students_took": 15,
            "students_passed": 10,
            "section": {
                "id": "sec-2",
                "section_number": "002",
                "instructor": {"first_name": "John", "last_name": "Smith"},
            },
        }

        mock_programs.return_value = [_PROGRAM]
        mock_term.return_value = _TERM
        mock_plos.return_value = [_PLO_1]
        mock_mapping.return_value = _MAPPING
        mock_courses.return_value = [_COURSE]
        mock_clos.return_value = [_CLO]
        mock_so.return_value = [so_1, so_2]

        result = get_plo_dashboard_tree(_INST_ID, term_id=_TERM_ID)

        clo = result["programs"][0]["plos"][0]["mapped_clos"][0]
        assert clo["students_took"] == 35  # 20 + 15
        assert clo["students_passed"] == 28  # 18 + 10
        assert len(clo["sections"]) == 2

    @patch(f"{_BASE}.get_section_outcomes_by_criteria")
    @patch(f"{_BASE}.get_course_outcomes")
    @patch(f"{_BASE}.get_courses_by_program")
    @patch(f"{_BASE}.get_latest_published_plo_mapping")
    @patch(f"{_BASE}.get_program_outcomes")
    @patch(f"{_BASE}.get_term_by_id")
    @patch(f"{_BASE}.get_programs_by_institution")
    def test_section_with_missing_instructor(
        self,
        mock_programs,
        mock_term,
        mock_plos,
        mock_mapping,
        mock_courses,
        mock_clos,
        mock_so,
    ):
        so_no_instructor = {
            **_SECTION_OUTCOME,
            "section": {
                "id": "sec-3",
                "section_number": "003",
                "instructor": {},
            },
        }
        mock_programs.return_value = [_PROGRAM]
        mock_term.return_value = _TERM
        mock_plos.return_value = [_PLO_1]
        mock_mapping.return_value = _MAPPING
        mock_courses.return_value = [_COURSE]
        mock_clos.return_value = [_CLO]
        mock_so.return_value = [so_no_instructor]

        result = get_plo_dashboard_tree(_INST_ID, term_id=_TERM_ID)
        sec = result["programs"][0]["plos"][0]["mapped_clos"][0]["sections"][0]
        assert sec["instructor_name"] == "Unassigned"
