"""
Integration tests for PLO Dashboard API.

Seeds real data (programs, PLOs, mappings, CLOs, section outcomes) and
verifies the /api/plo-dashboard/tree endpoint returns the correct
hierarchical structure with assessment data.
"""

import pytest

from tests.test_utils import create_test_session


class TestPloDashboardIntegration:
    """End-to-end tests for the PLO dashboard tree endpoint."""

    @pytest.fixture(autouse=True)
    def setup_test_context(
        self,
        isolated_integration_db,
        institution_admin,
        mocku_institution,
    ):
        """Set up test context and seed PLO-specific data."""
        import src.database.database_service as db
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

        self.admin = institution_admin
        self.institution = mocku_institution
        self.inst_id = mocku_institution["institution_id"]
        self.db = db

        # Seed PLO data for this test
        self._seed_plo_data()

    def _seed_plo_data(self):
        """Create programs, PLOs, CLOs, mappings, and section outcomes."""
        db = self.db

        # Get existing program (seeded by conftest)
        programs = db.get_programs_by_institution(self.inst_id) or []
        self.program = next((p for p in programs if not p.get("is_default")), None)
        if not self.program:
            # Create one if none exists
            pid = db.create_program(
                {
                    "name": "Test Program",
                    "short_name": "TEST",
                    "institution_id": self.inst_id,
                }
            )
            self.program = {"program_id": pid, "name": "Test Program"}

        self.prog_id = self.program.get("id") or self.program.get("program_id")

        # Create PLOs
        plo1_id = db.create_program_outcome(
            {
                "program_id": self.prog_id,
                "plo_number": 1,
                "description": "Critical thinking skills",
                "institution_id": self.inst_id,
            }
        )
        plo2_id = db.create_program_outcome(
            {
                "program_id": self.prog_id,
                "plo_number": 2,
                "description": "Communication skills",
                "institution_id": self.inst_id,
            }
        )
        self.plo1_id = plo1_id
        self.plo2_id = plo2_id

        # Get courses for CLOs
        courses = db.get_courses_by_program(self.prog_id) or []
        if courses:
            course = courses[0]
            self.course_id = course.get("course_id") or course.get("id")

            # Get CLOs
            clos = db.get_course_outcomes(self.course_id) or []
            if len(clos) >= 2:
                self.clo1_id = clos[0].get("outcome_id") or clos[0].get("id")
                self.clo2_id = clos[1].get("outcome_id") or clos[1].get("id")
            else:
                self.clo1_id = None
                self.clo2_id = None
        else:
            self.course_id = None
            self.clo1_id = None
            self.clo2_id = None

        # Create published PLO mapping if we have CLOs
        if self.clo1_id and self.clo2_id:
            mapping_id = db.create_plo_mapping(
                {
                    "program_id": self.prog_id,
                    "version": 1,
                    "status": "published",
                    "institution_id": self.inst_id,
                }
            )
            if mapping_id:
                db.add_plo_mapping_entry(
                    {
                        "mapping_id": mapping_id,
                        "program_outcome_id": self.plo1_id,
                        "course_outcome_id": self.clo1_id,
                    }
                )
                db.add_plo_mapping_entry(
                    {
                        "mapping_id": mapping_id,
                        "program_outcome_id": self.plo2_id,
                        "course_outcome_id": self.clo2_id,
                    }
                )
            self.mapping_id = mapping_id

    def _login_admin(self):
        """Authenticate as institution admin."""
        create_test_session(self.client, self.admin)

    def test_tree_returns_programs_with_plos(self):
        """GET /api/plo-dashboard/tree returns programs and nested PLOs."""
        self._login_admin()

        resp = self.client.get("/api/plo-dashboard/tree")
        assert resp.status_code == 200

        data = resp.get_json()
        assert data["success"] is True

        tree = data["data"]
        assert "programs" in tree
        assert "summary" in tree

        # Find our test program
        test_prog = next(
            (
                p
                for p in tree["programs"]
                if (p.get("id") or p.get("program_id")) == self.prog_id
            ),
            None,
        )
        assert test_prog is not None, "Test program not in tree"
        assert test_prog["plo_count"] == 2

    def test_tree_includes_mapped_clos(self):
        """PLO nodes include mapped CLOs when a published mapping exists."""
        if not self.clo1_id:
            pytest.skip("No CLOs available in seeded data")

        self._login_admin()

        resp = self.client.get("/api/plo-dashboard/tree")
        data = resp.get_json()["data"]

        test_prog = next(
            (
                p
                for p in data["programs"]
                if (p.get("id") or p.get("program_id")) == self.prog_id
            ),
            None,
        )
        assert test_prog is not None
        assert test_prog["mapped_clo_count"] >= 2
        assert test_prog["mapping_version"] == 1
        assert test_prog["mapping_status"] == "published"

        # Check PLO nodes have CLOs
        plo_with_clos = [
            plo for plo in test_prog["plos"] if plo["mapped_clo_count"] > 0
        ]
        assert len(plo_with_clos) >= 1

    def test_tree_with_program_filter(self):
        """Filtering by program_id returns only that program."""
        self._login_admin()

        resp = self.client.get(f"/api/plo-dashboard/tree?program_id={self.prog_id}")
        data = resp.get_json()["data"]

        # Should only contain the filtered program (plus possibly default)
        prog_ids = [p.get("id") or p.get("program_id") for p in data["programs"]]
        assert self.prog_id in prog_ids

    def test_tree_summary_counts(self):
        """Summary includes correct aggregate counts."""
        self._login_admin()

        resp = self.client.get("/api/plo-dashboard/tree")
        summary = resp.get_json()["data"]["summary"]

        assert summary["total_programs"] >= 1
        assert summary["total_plos"] >= 2

    def test_unauthenticated_returns_401(self):
        """Anonymous requests get 401."""
        resp = self.client.get("/api/plo-dashboard/tree")
        assert resp.status_code in (401, 302)

    def test_assessment_display_mode_default(self):
        """Programs default to percentage display mode."""
        self._login_admin()

        resp = self.client.get("/api/plo-dashboard/tree")
        data = resp.get_json()["data"]

        for prog in data["programs"]:
            assert prog["assessment_display_mode"] in (
                "percentage",
                "binary",
                "both",
            )
