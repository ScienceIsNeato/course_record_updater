"""
Course/Program/Section Management API Routes

Provides REST APIs for administrative CRUD operations:
- Programs: Update program metadata
- Courses: Duplicate courses (with optional program assignment)
- Sections: Update section metadata

Used by demo automation and admin interfaces.
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request

import src.database.database_service as db
from src.services.auth_service import permission_required
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

management_bp = Blueprint("management", __name__, url_prefix="/api/management")


@management_bp.route("/programs/<program_id>", methods=["PUT"])
@permission_required("manage_programs")
def update_program(program_id: str) -> tuple[Dict[str, Any], int]:
    """
    Update a program's metadata.

    Request body:
    {
        "name": "Program Name (optional)",
        "short_name": "SHORT (optional)",
        "description": "Program description (optional)"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Get existing program to verify it exists
        program = db.get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": "Program not found"}), 404

        # Update fields if provided
        updates = {}
        if "name" in data:
            updates["name"] = data["name"]
        if "short_name" in data:
            updates["short_name"] = data["short_name"]
        if "description" in data:
            updates["description"] = data["description"]

        if not updates:
            return jsonify({"success": False, "error": "No fields to update"}), 400

        # Perform update
        success = db.update_program(program_id, updates)

        if success:
            logger.info(f"Program {logger.sanitize(program_id)} updated via API")
            return jsonify({"success": True, "program_id": program_id}), 200
        else:
            return jsonify({"success": False, "error": "Update failed"}), 500

    except Exception as e:
        logger.error(f"Error updating program: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@management_bp.route("/courses/<course_id>/duplicate", methods=["POST"])
@permission_required("manage_courses")
def duplicate_course(course_id: str) -> tuple[Dict[str, Any], int]:
    """
    Duplicate a course with a new course number.

    Request body:
    {
        "new_course_number": "COURSE-###-V2",
        "program_ids": ["program_id_1", "program_id_2"]  // optional
    }
    """
    try:
        data = request.get_json()
        if not data or "new_course_number" not in data:
            return (
                jsonify({"success": False, "error": "new_course_number required"}),
                400,
            )

        new_course_number = data["new_course_number"]
        program_ids = data.get("program_ids", [])

        # Get source course
        source_course = db.get_course_by_id(course_id)
        if not source_course:
            return jsonify({"success": False, "error": "Source course not found"}), 404

        # Check if new course number already exists
        existing = db.get_course_by_number(
            new_course_number, source_course["institution_id"]
        )
        if existing:
            return (
                jsonify({"success": False, "error": "Course number already exists"}),
                409,
            )

        # Create new course
        new_course_data = {
            "course_number": new_course_number,
            "course_title": source_course["course_title"],
            "department": source_course.get("department"),
            "credit_hours": source_course.get("credit_hours"),
            "institution_id": source_course["institution_id"],
            "active": True,
        }

        new_course_id = db.create_course(new_course_data)
        if not new_course_id:
            return jsonify({"success": False, "error": "Failed to create course"}), 500

        # Attach to programs if specified
        if program_ids:
            for program_id in program_ids:
                db.add_course_to_program(new_course_id, program_id)
        else:
            # Copy program attachments from source course
            source_programs = db.get_programs_for_course(course_id)
            for program in source_programs:
                db.add_course_to_program(new_course_id, program["id"])

        logger.info(
            f"Course {logger.sanitize(course_id)} duplicated to {logger.sanitize(new_course_number)} via API"
        )
        return (
            jsonify(
                {
                    "success": True,
                    "course_id": new_course_id,
                    "course_number": new_course_number,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error duplicating course: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@management_bp.route("/sections/<section_id>", methods=["PUT"])
@permission_required("submit_assessments")
def update_section(section_id: str) -> tuple[Dict[str, Any], int]:
    """
    Update a section's assessment data.

    Request body:
    {
        "students_passed": 20 (optional),
        "students_dfic": 5 (optional),
        "narrative_celebrations": "What went well..." (optional),
        "narrative_challenges": "What didn't..." (optional),
        "narrative_changes": "What to change..." (optional)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Get existing section to verify it exists
        section = db.get_section_by_id(section_id)
        if not section:
            return jsonify({"success": False, "error": "Section not found"}), 404

        # Build updates dict
        updates = {}
        if "students_passed" in data:
            updates["students_passed"] = int(data["students_passed"])
        if "students_dfic" in data:
            updates["students_dfic"] = int(data["students_dfic"])
        if "narrative_celebrations" in data:
            updates["narrative_celebrations"] = data["narrative_celebrations"]
        if "narrative_challenges" in data:
            updates["narrative_challenges"] = data["narrative_challenges"]
        if "narrative_changes" in data:
            updates["narrative_changes"] = data["narrative_changes"]

        if not updates:
            return jsonify({"success": False, "error": "No fields to update"}), 400

        # Perform update
        success = db.update_course_section(section_id, updates)

        if success:
            logger.info(f"Section {logger.sanitize(section_id)} updated via API")
            return jsonify({"success": True, "section_id": section_id}), 200
        else:
            return jsonify({"success": False, "error": "Update failed"}), 500

    except Exception as e:
        logger.error(f"Error updating section: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
