"""Unit tests for PLO API routes (src/api/routes/plos.py).

Tests exercise the HTTP endpoints for PLO template CRUD and the
versioned PLO↔CLO mapping draft/publish workflow.

All tests use the database directly (no mocks) via unit test fixtures
that auto-reset between tests.
"""

import pytest

import src.database.database_service as database_service
from src.app import app
from tests.test_utils import create_test_session

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

INST_DATA = {
    "name": "PLO Route Test University",
    "short_name": "PRTU",
    "admin_email": "admin@prtu.edu",
    "created_by": "system",
}


@pytest.fixture
def client():
    """Flask test client with an authenticated site-admin session."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth(client, institution_id="inst-1"):
    """Set up an admin session for the client."""
    create_test_session(
        client,
        {
            "user_id": "admin-user",
            "email": "admin@test.edu",
            "role": "site_admin",
            "first_name": "Admin",
            "last_name": "Test",
            "institution_id": institution_id,
            "program_ids": [],
            "display_name": "Admin Test",
        },
    )


def _setup_program(suffix=""):
    """Create an institution + program, returning (inst_id, program_id)."""
    inst_id = database_service.create_institution(
        {**INST_DATA, "name": f"PLO Route Uni {suffix}", "short_name": f"PRU{suffix}"}
    )
    prog_id = database_service.create_program(
        {
            "name": f"CS {suffix}",
            "short_name": f"CS{suffix}",
            "institution_id": inst_id,
        }
    )
    return inst_id, prog_id


def _setup_user(inst_id, email="route-admin@test.edu"):
    """Create a user and return user_id."""
    return database_service.create_user(
        {
            "email": email,
            "first_name": "Route",
            "last_name": "Admin",
            "role": "institution_admin",
            "institution_id": inst_id,
            "account_status": "active",
        }
    )


def _setup_course_and_clo(inst_id, number="CS101", clo_desc="Test CLO"):
    """Create a course + CLO, return (course_id, clo_id)."""
    course_id = database_service.create_course(
        {
            "course_number": number,
            "course_title": f"Intro {number}",
            "department": "CS",
            "institution_id": inst_id,
        }
    )
    clo_id = database_service.create_course_outcome(
        {
            "course_id": course_id,
            "clo_number": 1,
            "description": clo_desc,
            "assessment_method": "exam",
            "active": True,
        }
    )
    return course_id, clo_id


# ---------------------------------------------------------------------------
# PLO template CRUD routes
# ---------------------------------------------------------------------------


class TestPLOCrudRoutes:
    """Tests for GET/POST/PUT/DELETE on /api/programs/<id>/plos."""

    def test_list_plos_empty(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("L1")
        resp = client.get(f"/api/programs/{prog_id}/plos")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["plos"] == []
        assert data["total"] == 0

    def test_create_plo(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("C1")
        resp = client.post(
            f"/api/programs/{prog_id}/plos",
            json={"plo_number": 1, "description": "Critical thinking"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data["plo"]["plo_number"] == 1
        assert data["plo"]["description"] == "Critical thinking"

    def test_create_plo_missing_fields(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("C2")
        resp = client.post(
            f"/api/programs/{prog_id}/plos",
            json={},
        )
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_create_plo_no_body(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("C3")
        resp = client.post(f"/api/programs/{prog_id}/plos")
        assert resp.status_code == 400

    def test_get_plo(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("G1")
        plo_id = database_service.create_program_outcome(
            {
                "program_id": prog_id,
                "institution_id": inst_id,
                "plo_number": 1,
                "description": "Problem solving",
            }
        )
        resp = client.get(f"/api/programs/{prog_id}/plos/{plo_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["plo"]["id"] == plo_id

    def test_get_plo_not_found(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("G2")
        resp = client.get(f"/api/programs/{prog_id}/plos/nonexistent")
        assert resp.status_code == 404

    def test_update_plo(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("U1")
        plo_id = database_service.create_program_outcome(
            {
                "program_id": prog_id,
                "institution_id": inst_id,
                "plo_number": 1,
                "description": "Original",
            }
        )
        resp = client.put(
            f"/api/programs/{prog_id}/plos/{plo_id}",
            json={"description": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["plo"]["description"] == "Updated"

    def test_update_plo_not_found(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("U2")
        resp = client.put(
            f"/api/programs/{prog_id}/plos/nonexistent",
            json={"description": "x"},
        )
        assert resp.status_code == 404

    def test_update_plo_no_body(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("U3")
        plo_id = database_service.create_program_outcome(
            {
                "program_id": prog_id,
                "institution_id": inst_id,
                "plo_number": 1,
                "description": "x",
            }
        )
        resp = client.put(f"/api/programs/{prog_id}/plos/{plo_id}")
        assert resp.status_code == 400

    def test_delete_plo(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("D1")
        plo_id = database_service.create_program_outcome(
            {
                "program_id": prog_id,
                "institution_id": inst_id,
                "plo_number": 1,
                "description": "Will be deactivated",
            }
        )
        resp = client.delete(f"/api/programs/{prog_id}/plos/{plo_id}")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        # Verify it's soft-deleted (not in active list)
        resp2 = client.get(f"/api/programs/{prog_id}/plos")
        assert resp2.get_json()["total"] == 0

    def test_delete_plo_not_found(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("D2")
        resp = client.delete(f"/api/programs/{prog_id}/plos/nonexistent")
        assert resp.status_code == 404

    def test_list_plos_program_not_found(self, client):
        _auth(client)
        resp = client.get("/api/programs/nonexistent-prog/plos")
        assert resp.status_code == 404

    def test_list_plos_include_inactive(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("LI")
        plo_id = database_service.create_program_outcome(
            {
                "program_id": prog_id,
                "institution_id": inst_id,
                "plo_number": 1,
                "description": "Will be inactive",
            }
        )
        database_service.delete_program_outcome(plo_id)

        # Default excludes inactive
        resp = client.get(f"/api/programs/{prog_id}/plos")
        assert resp.get_json()["total"] == 0

        # include_inactive=true shows it
        resp2 = client.get(f"/api/programs/{prog_id}/plos?include_inactive=true")
        assert resp2.get_json()["total"] == 1


# ---------------------------------------------------------------------------
# PLO Mapping draft lifecycle routes
# ---------------------------------------------------------------------------


class TestPLOMappingDraftRoutes:
    """Tests for draft create/get/discard endpoints."""

    def test_create_draft(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MD1")
        resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["mapping"]["status"] == "draft"
        assert data["mapping"]["entries"] == []

    def test_create_draft_idempotent(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MD2")
        r1 = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        r2 = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        assert r1.get_json()["mapping"]["id"] == r2.get_json()["mapping"]["id"]

    def test_create_draft_program_not_found(self, client):
        _auth(client)
        resp = client.post("/api/programs/nonexistent/plo-mappings/draft")
        assert resp.status_code == 404

    def test_get_draft(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MD3")
        client.post(f"/api/programs/{prog_id}/plo-mappings/draft")

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/draft")
        assert resp.status_code == 200
        assert resp.get_json()["mapping"]["status"] == "draft"

    def test_get_draft_not_found(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MD4")
        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/draft")
        assert resp.status_code == 404

    def test_discard_draft(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MD5")
        client.post(f"/api/programs/{prog_id}/plo-mappings/draft")

        resp = client.delete(f"/api/programs/{prog_id}/plo-mappings/draft")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        # Verify it's gone
        resp2 = client.get(f"/api/programs/{prog_id}/plo-mappings/draft")
        assert resp2.status_code == 404

    def test_discard_draft_not_found(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MD6")
        resp = client.delete(f"/api/programs/{prog_id}/plo-mappings/draft")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PLO Mapping entries routes
# ---------------------------------------------------------------------------


class TestPLOMappingEntryRoutes:
    """Tests for adding/removing PLO↔CLO mapping entries."""

    def test_add_and_remove_entry(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("ME1")
        plo_id = database_service.create_program_outcome(
            {
                "program_id": prog_id,
                "institution_id": inst_id,
                "plo_number": 1,
                "description": "PLO 1",
            }
        )
        _, clo_id = _setup_course_and_clo(inst_id, "ME101")

        # Create draft
        draft_resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mapping_id = draft_resp.get_json()["mapping"]["id"]

        # Add entry
        add_resp = client.post(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/entries",
            json={"program_outcome_id": plo_id, "course_outcome_id": clo_id},
        )
        assert add_resp.status_code == 201
        entry_id = add_resp.get_json()["entry_id"]
        assert entry_id is not None

        # Remove entry
        del_resp = client.delete(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/entries/{entry_id}"
        )
        assert del_resp.status_code == 200
        assert del_resp.get_json()["success"] is True

    def test_add_entry_missing_fields(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("ME2")
        draft_resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mapping_id = draft_resp.get_json()["mapping"]["id"]

        resp = client.post(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/entries",
            json={"program_outcome_id": "x"},
        )
        assert resp.status_code == 400
        assert "course_outcome_id" in resp.get_json()["error"]

    def test_remove_entry_not_found(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("ME3")
        draft_resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mapping_id = draft_resp.get_json()["mapping"]["id"]

        resp = client.delete(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/entries/nonexistent"
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PLO Mapping publish routes
# ---------------------------------------------------------------------------


class TestPLOMappingPublishRoutes:
    """Tests for publishing a draft mapping."""

    def test_publish_draft(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MP1")
        plo_id = database_service.create_program_outcome(
            {
                "program_id": prog_id,
                "institution_id": inst_id,
                "plo_number": 1,
                "description": "PLO 1",
            }
        )
        _, clo_id = _setup_course_and_clo(inst_id, "MP101")

        draft_resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mapping_id = draft_resp.get_json()["mapping"]["id"]

        client.post(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/entries",
            json={"program_outcome_id": plo_id, "course_outcome_id": clo_id},
        )

        pub_resp = client.post(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/publish",
            json={"description": "Initial mapping"},
        )
        assert pub_resp.status_code == 200
        data = pub_resp.get_json()
        assert data["mapping"]["version"] == 1
        assert data["mapping"]["status"] == "published"
        assert data["mapping"]["description"] == "Initial mapping"

    def test_publish_without_description(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MP2")
        draft_resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mapping_id = draft_resp.get_json()["mapping"]["id"]

        pub_resp = client.post(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/publish"
        )
        assert pub_resp.status_code == 200
        assert pub_resp.get_json()["mapping"]["version"] == 1


# ---------------------------------------------------------------------------
# PLO Mapping retrieval routes
# ---------------------------------------------------------------------------


class TestPLOMappingRetrievalRoutes:
    """Tests for listing/fetching published mapping versions."""

    def _publish_versions(self, client, prog_id, count=2):
        """Helper to publish N versions. Returns list of published mapping dicts."""
        published = []
        for i in range(count):
            draft = client.post(
                f"/api/programs/{prog_id}/plo-mappings/draft"
            ).get_json()["mapping"]
            pub = client.post(
                f"/api/programs/{prog_id}/plo-mappings/{draft['id']}/publish",
                json={"description": f"v{i + 1}"},
            ).get_json()["mapping"]
            published.append(pub)
        return published

    def test_list_published_mappings(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MR1")
        self._publish_versions(client, prog_id, count=3)

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 3
        assert [m["version"] for m in data["mappings"]] == [1, 2, 3]

    def test_get_latest_published(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MR2")
        self._publish_versions(client, prog_id, count=3)

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/latest")
        assert resp.status_code == 200
        assert resp.get_json()["mapping"]["version"] == 3

    def test_get_latest_published_none(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MR3")
        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/latest")
        assert resp.status_code == 404

    def test_get_mapping_by_version(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MR4")
        self._publish_versions(client, prog_id, count=2)

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/version/1")
        assert resp.status_code == 200
        assert resp.get_json()["mapping"]["version"] == 1

    def test_get_mapping_by_version_not_found(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MR5")
        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/version/99")
        assert resp.status_code == 404

    def test_get_mapping_by_id(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MR6")
        versions = self._publish_versions(client, prog_id, count=1)
        mapping_id = versions[0]["id"]

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/{mapping_id}")
        assert resp.status_code == 200
        assert resp.get_json()["mapping"]["id"] == mapping_id

    def test_get_mapping_by_id_not_found(self, client):
        _auth(client)
        inst_id, prog_id = _setup_program("MR7")
        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Matrix / cross-cutting query routes
# ---------------------------------------------------------------------------


def _setup_program_with_courses(suffix, num_courses=2, clos_per_course=2):
    """Create a fully wired program with courses linked and CLOs.

    Returns (inst_id, prog_id, [(course_id, [clo_id, ...]), ...]).
    """
    inst_id, prog_id = _setup_program(suffix)
    courses = []
    for i in range(num_courses):
        course_id = database_service.create_course(
            {
                "course_number": f"CS{suffix}{i}",
                "course_title": f"Course {suffix} {i}",
                "department": "CS",
                "institution_id": inst_id,
            }
        )
        database_service.add_course_to_program(course_id, prog_id)
        clo_ids = []
        for j in range(clos_per_course):
            clo_id = database_service.create_course_outcome(
                {
                    "course_id": course_id,
                    "clo_number": j + 1,
                    "description": f"CLO {suffix} C{i} #{j+1}",
                    "assessment_method": "exam",
                    "active": True,
                }
            )
            clo_ids.append(clo_id)
        courses.append((course_id, clo_ids))
    return inst_id, prog_id, courses


class TestPLOMappingMatrixRoutes:
    """Tests for GET /api/programs/<id>/plo-mappings/matrix."""

    def test_matrix_empty_program(self, client):
        """Matrix with no courses, PLOs, or mappings."""
        _auth(client)
        inst_id, prog_id = _setup_program("MX1")

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/matrix")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["plos"] == []
        assert data["courses"] == []
        assert data["matrix"] == {}
        # No draft or published mapping yet
        assert data["mapping"] is None

    def test_matrix_with_draft_entries(self, client):
        """Matrix populates cells from a draft mapping."""
        _auth(client)
        inst_id, prog_id, courses = _setup_program_with_courses("MX2")
        user_id = _setup_user(inst_id, email="mx2@test.edu")

        # Create PLOs
        plo_resp = client.post(
            f"/api/programs/{prog_id}/plos",
            json={"plo_number": 1, "description": "PLO MX2-1"},
        )
        plo_id = plo_resp.get_json()["plo"]["id"]

        # Create draft & add an entry
        draft_resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mapping_id = draft_resp.get_json()["mapping"]["id"]
        clo_id = courses[0][1][0]  # first CLO of first course
        client.post(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/entries",
            json={"program_outcome_id": plo_id, "course_outcome_id": clo_id},
        )

        # Fetch matrix
        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/matrix")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["plos"]) == 1
        assert len(data["courses"]) == 2
        # Matrix should show the single entry
        matrix = data["matrix"]
        assert plo_id in matrix
        assert clo_id in matrix[plo_id]
        assert matrix[plo_id][clo_id] is not None  # has entry_id

    def test_matrix_with_explicit_mapping_id(self, client):
        """Matrix can target a specific mapping via query param."""
        _auth(client)
        inst_id, prog_id, courses = _setup_program_with_courses("MX3")
        _setup_user(inst_id, email="mx3@test.edu")

        # Create & publish one version
        draft_resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mapping_id = draft_resp.get_json()["mapping"]["id"]
        client.post(f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/publish")

        resp = client.get(
            f"/api/programs/{prog_id}/plo-mappings/matrix",
            query_string={"mapping_id": mapping_id},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["mapping"]["id"] == mapping_id

    def test_matrix_with_version_param(self, client):
        """Matrix can target a specific version number."""
        _auth(client)
        inst_id, prog_id, courses = _setup_program_with_courses("MX4")
        _setup_user(inst_id, email="mx4@test.edu")

        # Publish version 1
        d = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mid = d.get_json()["mapping"]["id"]
        client.post(f"/api/programs/{prog_id}/plo-mappings/{mid}/publish")

        resp = client.get(
            f"/api/programs/{prog_id}/plo-mappings/matrix",
            query_string={"version": "1"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["mapping"]["version"] == 1

    def test_matrix_courses_include_clos(self, client):
        """Each course in the response includes its CLOs."""
        _auth(client)
        inst_id, prog_id, courses = _setup_program_with_courses(
            "MX5", num_courses=1, clos_per_course=3
        )

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/matrix")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["courses"]) == 1
        assert len(data["courses"][0]["clos"]) == 3


class TestPLOUnmappedCLOsRoutes:
    """Tests for GET /api/programs/<id>/plo-mappings/unmapped-clos."""

    def test_all_clos_unmapped_when_no_mapping(self, client):
        """All CLOs are unmapped when no mapping exists."""
        _auth(client)
        inst_id, prog_id, courses = _setup_program_with_courses("UM1")

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/unmapped-clos")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        total_clos = sum(len(clos) for _, clos in courses)
        assert data["count"] == total_clos

    def test_mapped_clo_excluded(self, client):
        """A CLO that has a mapping entry should not appear in unmapped list."""
        _auth(client)
        inst_id, prog_id, courses = _setup_program_with_courses(
            "UM2", num_courses=1, clos_per_course=3
        )
        user_id = _setup_user(inst_id, email="um2@test.edu")

        # Create a PLO and a draft with one CLO mapped
        plo_resp = client.post(
            f"/api/programs/{prog_id}/plos",
            json={"plo_number": 1, "description": "PLO UM2"},
        )
        plo_id = plo_resp.get_json()["plo"]["id"]

        draft_resp = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mapping_id = draft_resp.get_json()["mapping"]["id"]
        mapped_clo = courses[0][1][0]
        client.post(
            f"/api/programs/{prog_id}/plo-mappings/{mapping_id}/entries",
            json={"program_outcome_id": plo_id, "course_outcome_id": mapped_clo},
        )

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/unmapped-clos")
        assert resp.status_code == 200
        data = resp.get_json()
        # 3 total CLOs, 1 mapped → 2 unmapped
        assert data["count"] == 2
        unmapped_ids = [c["outcome_id"] for c in data["unmapped_clos"]]
        assert mapped_clo not in unmapped_ids

    def test_unmapped_with_explicit_mapping_id(self, client):
        """Unmapped CLOs can target a specific mapping via query param."""
        _auth(client)
        inst_id, prog_id, courses = _setup_program_with_courses("UM3")
        _setup_user(inst_id, email="um3@test.edu")

        # Create and publish a draft
        d = client.post(f"/api/programs/{prog_id}/plo-mappings/draft")
        mid = d.get_json()["mapping"]["id"]
        client.post(f"/api/programs/{prog_id}/plo-mappings/{mid}/publish")

        resp = client.get(
            f"/api/programs/{prog_id}/plo-mappings/unmapped-clos",
            query_string={"mapping_id": mid},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_unmapped_includes_course_info(self, client):
        """Each unmapped CLO includes its parent course info."""
        _auth(client)
        inst_id, prog_id, courses = _setup_program_with_courses(
            "UM4", num_courses=1, clos_per_course=1
        )

        resp = client.get(f"/api/programs/{prog_id}/plo-mappings/unmapped-clos")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 1
        clo = data["unmapped_clos"][0]
        assert "course" in clo
        assert clo["course"]["course_id"] == courses[0][0]
