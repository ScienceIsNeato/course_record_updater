#!/usr/bin/env python3
"""
Demo State Advancer

Single entry point for advancing the demo environment to specific states
or generating artifacts required for the walkthrough.

Usage:
    python scripts/advance_demo.py [target_state] --env [dev|e2e]

Targets:
    generate_logs   - Simulates Phase 2/3 actions (Invites, Imports) to generate log artifacts.
    semester_end    - Fast-forwards to Phase 4 (Submissions, Duplications, Reminders).
"""

import argparse
import logging
import os
import sys
import time
from types import ModuleType
from typing import Any

import pandas as pd
from flask import Flask

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/demo_advancer.log"), logging.StreamHandler()],
)
logger = logging.getLogger("demo_advancer")


def setup_env(env_name: str = "dev") -> None:
    db_mapping = {
        "dev": "sqlite:///course_records_dev.db",
        "e2e": "sqlite:///course_records_e2e.db",
        "prod": "sqlite:///course_records.db",
    }
    url = db_mapping.get(env_name, db_mapping["dev"])
    os.environ["DATABASE_URL"] = url
    os.environ["FLASK_ENV"] = "development"
    logger.info(f"Using database: {url}")


def run_generate_logs(app: Flask, db: ModuleType) -> None:
    """Simulates Phase 2/3 actions (Invites, Imports) to generate log artifacts."""
    from src.services.auth_service import UserRole
    from src.services.import_service import ConflictStrategy, ImportService
    from src.services.invitation_service import InvitationService

    logger.info("=== Target: Generate Logs (Phase 2/3) ===")

    # 1. Find Admin User
    admin = db.get_user_by_email("demo2025.admin@example.com")
    if not admin:
        logger.error("Admin user not found. Please seed database first.")
        return

    institution_id = admin.get("institution_id")
    admin_id = admin.get("user_id") or admin.get("id")

    # 2. Simulate Instructor Invitation
    logger.info("Simulating Instructor Invitation...")
    new_email = "new.faculty@demo.example.com"

    existing = db.get_user_by_email(new_email)
    if existing:
        logger.info(f"User {new_email} already exists, skipping invite.")
    else:
        try:
            invitation_data = InvitationService.create_invitation(
                inviter_user_id=admin_id,
                inviter_email=admin["email"],
                invitee_email=new_email,
                invitee_role=UserRole.INSTRUCTOR.value,
                institution_id=institution_id,
                personal_message="Welcome to the Biology department!",
            )

            if invitation_data:
                sent, email_error = InvitationService.send_invitation(invitation_data)
                if sent and not email_error:
                    logger.info(f"Invitation sent to {new_email}")
                else:
                    logger.error(
                        f"Failed to send invitation email{f': {email_error}' if email_error else ''}"
                    )
            else:
                logger.error("Failed to create invitation record")
        except Exception as e:
            logger.error(f"Exception inviting user: {e}")

    # 3. Simulate Course Import
    logger.info("Simulating Course Import...")

    excel_path = "demo_data/course_import_template.xlsx"
    os.makedirs("demo_data", exist_ok=True)

    data = {
        "course": ["CHEM-101", "PHYS-101"],
        "email": ["chem.prof@demo.example.com", "phys.prof@demo.example.com"],
        "Term": ["2024 Fall", "2024 Fall"],
        "students": [25, 30],
    }
    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False)
    logger.info(f"Created import file: {excel_path}")

    try:
        service = ImportService(institution_id=institution_id, verbose=True)
        result = service.import_excel_file(
            file_path=excel_path,
            conflict_strategy=ConflictStrategy.USE_THEIRS,
            dry_run=False,
            adapter_id="cei_excel_format_v1",
        )

        logger.info(
            f"Import Result: Success={result.success}, Created={result.records_created}, Updated={result.records_updated}"
        )
        if result.errors:
            logger.error(f"Import Errors: {result.errors}")

    except Exception as e:
        logger.error(f"Import failed: {e}")


def run_semester_end(app: Flask, db: ModuleType) -> None:
    """Fast-forwards to Phase 4 (Submissions, Duplications, Reminders)."""
    from src.models.models import CourseOutcome
    from src.services.bulk_email_service import BulkEmailService
    from src.services.clo_workflow_service import CLOWorkflowService
    from src.utils.constants import CLOStatus

    logger.info("=== Target: Semester End (Phase 4 Setup) ===")

    # 1. Find Users
    morgan = db.get_user_by_email("dr.morgan@demo.example.com")
    patel = db.get_user_by_email("dr.patel@demo.example.com")
    admin = db.get_user_by_email("demo2025.admin@example.com")

    if not morgan or not patel or not admin:
        logger.error(
            "Users not found. Please run 'python scripts/seed_db.py --demo --clear --env dev' first."
        )
        return

    institution_id = morgan.get("institution_id")
    morgan_id = morgan.get("user_id") or morgan.get("id")
    patel_id = patel.get("user_id") or patel.get("id")
    admin_id = admin.get("user_id") or admin.get("id")

    # 2. Find Courses
    biol101 = db.get_course_by_number("BIOL-101", institution_id)
    zool101 = db.get_course_by_number("ZOOL-101", institution_id)

    if not biol101:
        logger.error("BIOL-101 not found.")
        return

    if not zool101:
        logger.error("ZOOL-101 not found.")
        return

    biol101_id = biol101.get("course_id") or biol101.get("id")
    zool101_id = zool101.get("course_id") or zool101.get("id")

    logger.info("Found users and courses. Creating CLOs...")

    # 3. Create CLOs (if not exist)
    def ensure_clo(
        course_id: str,
        clo_num: Any,
        desc: str,
        method: str = "Exam Question",
    ) -> str:
        existing = db.get_course_outcomes(course_id)
        for clo in existing:
            if str(clo.get("clo_number")) == str(clo_num):
                outcome_id = clo.get("outcome_id") or clo.get("id")
                if outcome_id is None:
                    logger.error(
                        "Existing CLO missing outcome id for course %s", course_id
                    )
                    raise RuntimeError("Existing CLO has no outcome id")
                return outcome_id

        schema = CourseOutcome.create_schema(
            course_id=course_id,
            clo_number=str(clo_num),
            description=desc,
            assessment_method=method,
        )
        schema["status"] = CLOStatus.ASSIGNED

        outcome_id = db.create_course_outcome(schema)
        if outcome_id is None:
            logger.error("Failed to create CLO %s for course %s", clo_num, course_id)
            raise RuntimeError("Failed to create course outcome")
        logger.info(f"Created CLO {clo_num} for course {course_id}")
        return outcome_id

    # Create CLOs for BIOL-101
    biol_clo1_id = ensure_clo(biol101_id, 1, "Analyze cell structures", "Lab Report")
    biol_clo2_id = ensure_clo(biol101_id, 2, "Explain metabolic pathways", "Final Exam")
    biol_clo3_id = ensure_clo(
        biol101_id, 3, "Apply scientific method", "Research Project"
    )

    # Create CLOs for ZOOL-101
    zool_clo1_id = ensure_clo(
        zool101_id, 1, "Identify vertebrate classes", "Field Observation"
    )
    zool_clo2_id = ensure_clo(zool101_id, 2, "Analyze animal behavior", "Lab Report")

    # 4. Submit BIOL-101 CLO 1 → Awaiting Approval (good data, ready to approve)
    logger.info("Simulating BIOL-101 CLO 1 submission (Morgan) → Awaiting Approval...")
    db.update_outcome_assessment(
        biol_clo1_id,
        students_took=25,
        students_passed=22,
        assessment_tool="Lab Report #4 - Microscopy",
    )
    CLOWorkflowService.submit_clo_for_approval(biol_clo1_id, morgan_id)
    logger.info(f"✓ BIOL-101 CLO 1: Awaiting Approval")

    # 5. Submit & Approve BIOL-101 CLO 2 → Approved
    logger.info(
        "Simulating BIOL-101 CLO 2 submission and approval (Morgan) → Approved..."
    )
    db.update_outcome_assessment(
        biol_clo2_id,
        students_took=24,
        students_passed=20,
        assessment_tool="Final Exam - Metabolic Pathways Section",
    )
    CLOWorkflowService.submit_clo_for_approval(biol_clo2_id, morgan_id)
    CLOWorkflowService.approve_clo(biol_clo2_id, admin_id)
    logger.info(f"✓ BIOL-101 CLO 2: Approved")

    # 6. Submit & Request Rework for ZOOL-101 CLO 1 → Needs Rework
    logger.info(
        "Simulating ZOOL-101 CLO 1 submission and rejection (Patel) → Needs Rework..."
    )
    db.update_outcome_assessment(
        zool_clo1_id, students_took=0, students_passed=0, assessment_tool="Pending tool"
    )
    CLOWorkflowService.submit_clo_for_approval(zool_clo1_id, patel_id)
    CLOWorkflowService.request_rework(
        zool_clo1_id,
        admin_id,
        "Please provide complete assessment data. Currently showing 0 students, which appears incomplete.",
    )
    logger.info(f"✓ ZOOL-101 CLO 1: Needs Rework")

    # 7. Mark BIOL-101 CLO 3 as NCI → Never Coming In
    logger.info("Marking BIOL-101 CLO 3 as Never Coming In...")
    CLOWorkflowService.mark_as_nci(
        biol_clo3_id,
        admin_id,
        "Instructor on extended leave; course not taught this semester.",
    )
    logger.info(f"✓ BIOL-101 CLO 3: Never Coming In")

    # 8. Submit ZOOL-101 CLO 2 → Awaiting Approval (second awaiting approval entry)
    logger.info("Simulating ZOOL-101 CLO 2 submission (Patel) → Awaiting Approval...")
    db.update_outcome_assessment(
        zool_clo2_id,
        students_took=18,
        students_passed=15,
        assessment_tool="Lab Report - Animal Behavior Analysis",
    )
    CLOWorkflowService.submit_clo_for_approval(zool_clo2_id, patel_id)
    logger.info(f"✓ ZOOL-101 CLO 2: Awaiting Approval")

    # 9. Simulate Course Duplication
    logger.info("Simulating Course Duplication for BIOL-101...")
    dup_course = db.get_course_by_number("BIOL-101-V2", institution_id)
    if not dup_course:
        dup_id = db.duplicate_course_record(
            biol101, overrides={"course_number": "BIOL-101-V2", "active": True}
        )
        if dup_id:
            logger.info(f"Successfully duplicated course. New ID: {dup_id}")
        else:
            logger.error("Failed to duplicate course.")
    else:
        logger.info("Duplicate course BIOL-101-V2 already exists.")

    # 10. Trigger Reminders
    logger.info("Triggering Reminder Runbook...")
    try:
        # Access private _db_service to get sqlite session
        session = db._db_service.sqlite.get_session()

        job_id = BulkEmailService.send_instructor_reminders(
            db=session,
            instructor_ids=[morgan_id, patel_id],
            created_by_user_id=admin_id,
            personal_message="Please complete your assessments by Friday.",
            term="Fall 2024",
        )
        logger.info(f"Bulk email job started: {job_id}")
        time.sleep(2)
        logger.info("Reminder job processing in background...")

    except Exception as e:
        logger.error(f"Failed to trigger reminders: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo State Advancer")
    parser.add_argument(
        "target",
        choices=["generate_logs", "semester_end"],
        help="Target state/action to run",
    )
    parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "e2e"],
        help="Environment to run against",
    )

    args = parser.parse_args()

    setup_env(args.env)

    # Import services AFTER env setup
    import src.database.database_service as db
    from src.app import app

    with app.app_context():
        if args.target == "generate_logs":
            run_generate_logs(app, db)
        elif args.target == "semester_end":
            run_semester_end(app, db)

    logger.info("Advance Complete.")


if __name__ == "__main__":
    main()
