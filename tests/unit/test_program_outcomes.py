"""Unit tests for Program Outcome (PLO) CRUD and versioned PLO mapping operations.

Tests cover:
- ProgramOutcome template CRUD (create, read, update, soft-delete)
- PloMapping draft/publish lifecycle (create draft, add/remove entries, publish)
- Version numbering (auto-increment, sequential)
- Draft-from-published copy (entries carried forward)
- PLO description snapshotting on publish
- Discard draft
- Edge cases (nonexistent IDs, empty programs, duplicate entries)
"""

import src.database.database_service as database_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_institution(suffix=""):
    """Create a test institution with unique name."""
    label = f"PLO Test University{suffix}"
    short = f"PLOU{suffix}"
    return database_service.create_institution(
        {
            "name": label,
            "short_name": short,
            "admin_email": f"admin@plou{suffix}.edu",
            "created_by": "system",
        }
    )


def _create_program(inst_id, name="Computer Science", short="CS"):
    """Create a test program."""
    return database_service.create_program(
        {
            "name": name,
            "short_name": short,
            "institution_id": inst_id,
        }
    )


def _create_user(inst_id, email="admin@test.edu"):
    """Create a test user."""
    return database_service.create_user(
        {
            "email": email,
            "first_name": "Test",
            "last_name": "Admin",
            "role": "institution_admin",
            "institution_id": inst_id,
            "account_status": "active",
        }
    )


def _create_course(inst_id, number="CS101", title="Intro to CS"):
    """Create a test course."""
    return database_service.create_course(
        {
            "course_number": number,
            "course_title": title,
            "department": "CS",
            "institution_id": inst_id,
        }
    )


def _create_clo(course_id, clo_number=1, description="Test CLO"):
    """Create a CLO (CourseOutcome) and return its ID."""
    return database_service.create_course_outcome(
        {
            "course_id": course_id,
            "clo_number": clo_number,
            "description": description,
            "assessment_method": "exam",
            "active": True,
        }
    )


def _create_plo(program_id, inst_id, plo_number=1, description="Test PLO"):
    """Create a PLO template and return its ID."""
    return database_service.create_program_outcome(
        {
            "program_id": program_id,
            "institution_id": inst_id,
            "plo_number": plo_number,
            "description": description,
        }
    )


# ---------------------------------------------------------------------------
# PLO CRUD
# ---------------------------------------------------------------------------


def test_create_program_outcome():
    """Create a PLO template and verify it exists."""
    inst_id = _create_institution("C1")
    program_id = _create_program(inst_id)

    plo_id = _create_plo(
        program_id,
        inst_id,
        plo_number=1,
        description="Students will demonstrate critical thinking",
    )

    assert plo_id is not None

    plo = database_service.get_program_outcome(plo_id)
    assert plo is not None
    assert plo["program_id"] == program_id
    assert plo["institution_id"] == inst_id
    assert plo["plo_number"] == 1
    assert plo["description"] == "Students will demonstrate critical thinking"
    assert plo["is_active"] is True


def test_create_multiple_plos_ordered():
    """Multiple PLOs are returned ordered by plo_number."""
    inst_id = _create_institution("C2")
    program_id = _create_program(inst_id)

    _create_plo(program_id, inst_id, plo_number=3, description="Third")
    _create_plo(program_id, inst_id, plo_number=1, description="First")
    _create_plo(program_id, inst_id, plo_number=2, description="Second")

    plos = database_service.get_program_outcomes(program_id)
    assert len(plos) == 3
    assert [p["plo_number"] for p in plos] == [1, 2, 3]
    assert [p["description"] for p in plos] == ["First", "Second", "Third"]


def test_get_program_outcomes_filters_inactive():
    """get_program_outcomes excludes inactive PLOs by default."""
    inst_id = _create_institution("R1")
    program_id = _create_program(inst_id)

    active_id = _create_plo(program_id, inst_id, 1, "Active PLO")
    inactive_id = _create_plo(program_id, inst_id, 2, "Will be deactivated")
    database_service.delete_program_outcome(inactive_id)

    active_only = database_service.get_program_outcomes(program_id)
    assert len(active_only) == 1
    assert active_only[0]["id"] == active_id

    all_plos = database_service.get_program_outcomes(program_id, include_inactive=True)
    assert len(all_plos) == 2


def test_get_program_outcome_nonexistent():
    """get_program_outcome returns None for nonexistent ID."""
    assert database_service.get_program_outcome("nonexistent-id") is None


def test_get_program_outcomes_empty_program():
    """get_program_outcomes returns empty list for a program with no PLOs."""
    inst_id = _create_institution("R3")
    program_id = _create_program(inst_id)
    assert database_service.get_program_outcomes(program_id) == []


def test_update_program_outcome():
    """Update a PLO description and verify the change."""
    inst_id = _create_institution("U1")
    program_id = _create_program(inst_id)

    plo_id = _create_plo(program_id, inst_id, 1, "Original description")

    result = database_service.update_program_outcome(
        plo_id, {"description": "Updated description"}
    )
    assert result is True

    plo = database_service.get_program_outcome(plo_id)
    assert plo["description"] == "Updated description"


def test_update_program_outcome_nonexistent():
    """update_program_outcome returns False for nonexistent ID."""
    assert (
        database_service.update_program_outcome(
            "nonexistent-id", {"description": "nope"}
        )
        is False
    )


def test_delete_program_outcome_soft():
    """delete_program_outcome sets is_active=False, not hard delete."""
    inst_id = _create_institution("D1")
    program_id = _create_program(inst_id)

    plo_id = _create_plo(program_id, inst_id, 1, "To be soft-deleted")
    assert database_service.delete_program_outcome(plo_id) is True

    active = database_service.get_program_outcomes(program_id)
    assert len(active) == 0

    all_plos = database_service.get_program_outcomes(program_id, include_inactive=True)
    assert len(all_plos) == 1
    assert all_plos[0]["is_active"] is False


def test_delete_program_outcome_nonexistent():
    """delete_program_outcome returns False for nonexistent ID."""
    assert database_service.delete_program_outcome("nonexistent-id") is False


# ---------------------------------------------------------------------------
# PLO Mapping — draft lifecycle
# ---------------------------------------------------------------------------


def test_create_draft_mapping():
    """get_or_create_plo_mapping_draft creates a new draft for a program."""
    inst_id = _create_institution("M1")
    program_id = _create_program(inst_id)
    user_id = _create_user(inst_id, "m1@test.edu")

    draft = database_service.get_or_create_plo_mapping_draft(program_id, user_id)

    assert draft is not None
    assert draft["program_id"] == program_id
    assert draft["status"] == "draft"
    assert draft["version"] is None
    assert draft["created_by_user_id"] == user_id
    assert draft["entries"] == []


def test_get_or_create_draft_idempotent():
    """Calling get_or_create twice returns the same draft."""
    inst_id = _create_institution("M2")
    program_id = _create_program(inst_id)

    draft1 = database_service.get_or_create_plo_mapping_draft(program_id)
    draft2 = database_service.get_or_create_plo_mapping_draft(program_id)

    assert draft1["id"] == draft2["id"]


def test_get_draft_none_when_absent():
    """get_plo_mapping_draft returns None when no draft exists."""
    inst_id = _create_institution("M3")
    program_id = _create_program(inst_id)

    assert database_service.get_plo_mapping_draft(program_id) is None


def test_add_and_remove_mapping_entries():
    """Add and remove PLO↔CLO links in a draft mapping."""
    inst_id = _create_institution("M4")
    program_id = _create_program(inst_id)
    course_id = _create_course(inst_id)
    plo_id = _create_plo(program_id, inst_id, 1, "PLO 1")
    clo_id = _create_clo(course_id, 1, "CLO 1")

    draft = database_service.get_or_create_plo_mapping_draft(program_id)
    entry_id = database_service.add_plo_mapping_entry(draft["id"], plo_id, clo_id)
    assert entry_id is not None

    # Verify entry exists
    refreshed = database_service.get_plo_mapping(draft["id"])
    assert len(refreshed["entries"]) == 1
    assert refreshed["entries"][0]["program_outcome_id"] == plo_id
    assert refreshed["entries"][0]["course_outcome_id"] == clo_id

    # Remove
    assert database_service.remove_plo_mapping_entry(entry_id) is True
    refreshed = database_service.get_plo_mapping(draft["id"])
    assert len(refreshed["entries"]) == 0


def test_remove_nonexistent_entry():
    """remove_plo_mapping_entry returns False for nonexistent ID."""
    assert database_service.remove_plo_mapping_entry("nonexistent") is False


def test_discard_draft():
    """discard_plo_mapping_draft deletes draft and its entries."""
    inst_id = _create_institution("M5")
    program_id = _create_program(inst_id)

    draft = database_service.get_or_create_plo_mapping_draft(program_id)
    assert database_service.discard_plo_mapping_draft(draft["id"]) is True

    # Draft is gone
    assert database_service.get_plo_mapping_draft(program_id) is None
    assert database_service.get_plo_mapping(draft["id"]) is None


def test_discard_nonexistent_draft():
    """discard_plo_mapping_draft returns False for nonexistent ID."""
    assert database_service.discard_plo_mapping_draft("nonexistent") is False


# ---------------------------------------------------------------------------
# PLO Mapping — publish
# ---------------------------------------------------------------------------


def test_publish_mapping_assigns_version():
    """Publishing a draft assigns version 1."""
    inst_id = _create_institution("P1")
    program_id = _create_program(inst_id)
    course_id = _create_course(inst_id)
    plo_id = _create_plo(program_id, inst_id, 1, "PLO 1")
    clo_id = _create_clo(course_id, 1, "CLO 1")

    draft = database_service.get_or_create_plo_mapping_draft(program_id)
    database_service.add_plo_mapping_entry(draft["id"], plo_id, clo_id)

    published = database_service.publish_plo_mapping(
        draft["id"], description="Initial mapping"
    )

    assert published["version"] == 1
    assert published["status"] == "published"
    assert published["description"] == "Initial mapping"
    assert published["published_at"] is not None
    assert len(published["entries"]) == 1


def test_publish_increments_version():
    """Second publish gets version 2."""
    inst_id = _create_institution("P2")
    program_id = _create_program(inst_id)
    course_id = _create_course(inst_id)
    plo_id = _create_plo(program_id, inst_id, 1, "PLO 1")
    clo1_id = _create_clo(course_id, 1, "CLO 1")
    clo2_id = _create_clo(course_id, 2, "CLO 2")

    # Version 1
    draft1 = database_service.get_or_create_plo_mapping_draft(program_id)
    database_service.add_plo_mapping_entry(draft1["id"], plo_id, clo1_id)
    v1 = database_service.publish_plo_mapping(draft1["id"])
    assert v1["version"] == 1

    # Version 2
    draft2 = database_service.get_or_create_plo_mapping_draft(program_id)
    database_service.add_plo_mapping_entry(draft2["id"], plo_id, clo2_id)
    v2 = database_service.publish_plo_mapping(draft2["id"])
    assert v2["version"] == 2


def test_publish_snapshots_plo_description():
    """Published entries capture the PLO description at publish time."""
    inst_id = _create_institution("P3")
    program_id = _create_program(inst_id)
    course_id = _create_course(inst_id)
    plo_id = _create_plo(program_id, inst_id, 1, "Original PLO text")
    clo_id = _create_clo(course_id, 1, "CLO 1")

    draft = database_service.get_or_create_plo_mapping_draft(program_id)
    database_service.add_plo_mapping_entry(draft["id"], plo_id, clo_id)
    published = database_service.publish_plo_mapping(draft["id"])

    assert published["entries"][0]["plo_description_snapshot"] == "Original PLO text"

    # Now update PLO and publish v2
    database_service.update_program_outcome(plo_id, {"description": "Updated text"})
    draft2 = database_service.get_or_create_plo_mapping_draft(program_id)
    v2 = database_service.publish_plo_mapping(draft2["id"])

    # v2 snapshot reflects updated text, v1 preserves original
    assert v2["entries"][0]["plo_description_snapshot"] == "Updated text"
    v1 = database_service.get_plo_mapping_by_version(program_id, 1)
    assert v1["entries"][0]["plo_description_snapshot"] == "Original PLO text"


# ---------------------------------------------------------------------------
# PLO Mapping — draft from published
# ---------------------------------------------------------------------------


def test_draft_copies_entries_from_latest_published():
    """New draft after a publish copies entries from the latest version."""
    inst_id = _create_institution("F1")
    program_id = _create_program(inst_id)
    course_id = _create_course(inst_id)
    plo_id = _create_plo(program_id, inst_id, 1, "PLO")
    clo1_id = _create_clo(course_id, 1, "CLO 1")
    clo2_id = _create_clo(course_id, 2, "CLO 2")

    # Publish v1 with 2 entries
    draft = database_service.get_or_create_plo_mapping_draft(program_id)
    database_service.add_plo_mapping_entry(draft["id"], plo_id, clo1_id)
    database_service.add_plo_mapping_entry(draft["id"], plo_id, clo2_id)
    database_service.publish_plo_mapping(draft["id"])

    # New draft should start with those 2 entries
    new_draft = database_service.get_or_create_plo_mapping_draft(program_id)
    assert len(new_draft["entries"]) == 2
    entry_clo_ids = {e["course_outcome_id"] for e in new_draft["entries"]}
    assert entry_clo_ids == {clo1_id, clo2_id}


# ---------------------------------------------------------------------------
# PLO Mapping — retrieval
# ---------------------------------------------------------------------------


def test_get_plo_mapping_by_version():
    """Retrieve a specific published version."""
    inst_id = _create_institution("G1")
    program_id = _create_program(inst_id)

    draft = database_service.get_or_create_plo_mapping_draft(program_id)
    database_service.publish_plo_mapping(draft["id"], "v1")

    result = database_service.get_plo_mapping_by_version(program_id, 1)
    assert result is not None
    assert result["version"] == 1
    assert result["description"] == "v1"


def test_get_plo_mapping_by_version_nonexistent():
    """Returns None for a version that doesn't exist."""
    inst_id = _create_institution("G2")
    program_id = _create_program(inst_id)
    assert database_service.get_plo_mapping_by_version(program_id, 99) is None


def test_get_published_plo_mappings():
    """Lists all published versions in order."""
    inst_id = _create_institution("G3")
    program_id = _create_program(inst_id)

    for i in range(3):
        draft = database_service.get_or_create_plo_mapping_draft(program_id)
        database_service.publish_plo_mapping(draft["id"], f"v{i + 1}")

    versions = database_service.get_published_plo_mappings(program_id)
    assert len(versions) == 3
    assert [v["version"] for v in versions] == [1, 2, 3]


def test_get_latest_published_plo_mapping():
    """Returns the highest-versioned published mapping."""
    inst_id = _create_institution("G4")
    program_id = _create_program(inst_id)

    for i in range(3):
        draft = database_service.get_or_create_plo_mapping_draft(program_id)
        database_service.publish_plo_mapping(draft["id"], f"v{i + 1}")

    latest = database_service.get_latest_published_plo_mapping(program_id)
    assert latest is not None
    assert latest["version"] == 3


def test_get_latest_published_none_when_empty():
    """Returns None when no published mapping exists."""
    inst_id = _create_institution("G5")
    program_id = _create_program(inst_id)
    assert database_service.get_latest_published_plo_mapping(program_id) is None


def test_get_plo_mapping_nonexistent():
    """get_plo_mapping returns None for nonexistent mapping."""
    assert database_service.get_plo_mapping("nonexistent") is None
