#!/usr/bin/env python3
"""
Setup Demo State (Phase 3 & 4 Prerequisites)

1. Creates CLOs for seeded courses (BIOL-201, ZOOL-101).
2. Submits assessments to creating "Awaiting Approval" state.
3. Simulates Course Duplication.
4. triggers Reminders.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/demo_setup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("demo_setup")

def setup_env(env_name="dev"):
    db_mapping = {
        "dev": "sqlite:///course_records_dev.db",
        "e2e": "sqlite:///course_records_e2e.db",
        "prod": "sqlite:///course_records.db",
    }
    url = db_mapping.get(env_name, db_mapping["dev"])
    os.environ["DATABASE_URL"] = url
    os.environ["FLASK_ENV"] = "development" # Ensure debug mode etc
    logger.info(f"Using database: {url}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="dev", choices=["dev", "e2e"])
    args = parser.parse_args()

    setup_env(args.env)

    # Import services AFTER env setup
    import database_service as db
    from models import CourseOutcome
    from clo_workflow_service import CLOWorkflowService
    from constants import CLOStatus
    from bulk_email_service import BulkEmailService
    from app import app # Import the Flask app instance
    
    with app.app_context():
        # 1. Find Users
        morgan = db.get_user_by_email("dr.morgan@demo.example.com")
        patel = db.get_user_by_email("dr.patel@demo.example.com")
        admin = db.get_user_by_email("demo2025.admin@example.com")
        
        if not morgan or not patel or not admin:
            logger.error("Users not found. Please run 'python scripts/seed_db.py --demo --clear --env dev' first.")
            return

        institution_id = morgan.get('institution_id')
        morgan_id = morgan.get('user_id') or morgan.get('id')
        patel_id = patel.get('user_id') or patel.get('id')
        admin_id = admin.get('user_id') or admin.get('id')

        # 2. Find Courses
        biol201 = db.get_course_by_number("BIOL-201", institution_id)
        zool101 = db.get_course_by_number("ZOOL-101", institution_id)

        if not biol201:
            logger.error("BIOL-201 not found.")
            return
        
        if not zool101:
            logger.error("ZOOL-101 not found.")
            return
            
        biol201_id = biol201.get('course_id') or biol201.get('id')
        zool101_id = zool101.get('course_id') or zool101.get('id')

        logger.info("Found users and courses. Creating CLOs...")

        # 3. Create CLOs (if not exist)
        # Helper to create CLO
        def ensure_clo(course_id, clo_num, desc, method="Exam Question"):
            # Check if exists
            existing = db.get_course_outcomes(course_id)
            for clo in existing:
                if str(clo.get('clo_number')) == str(clo_num):
                    return clo.get('outcome_id') or clo.get('id')
            
            schema = CourseOutcome.create_schema(
                course_id=course_id,
                clo_number=str(clo_num),
                description=desc,
                assessment_method=method
            )
            # Force status to assigned via dictionary injection (model agnostic)
            schema["status"] = CLOStatus.ASSIGNED
            
            outcome_id = db.create_course_outcome(schema)
            logger.info(f"Created CLO {clo_num} for course {course_id}")
            return outcome_id

        biol_clo1_id = ensure_clo(biol201_id, 1, "Analyze cell structures", "Lab Report")
        biol_clo2_id = ensure_clo(biol201_id, 2, "Explain metabolic pathways", "Final Exam")
        
        zool_clo1_id = ensure_clo(zool101_id, 1, "Identify vertebrate classes", "Field Observation")

        # 4. Submit BIOL-201 CLO 1 (Approvable)
        logger.info("Simulating BIOL-201 submission (Morgan)...")
        db.update_outcome_assessment(
            biol_clo1_id,
            students_took=25,
            students_passed=22,
            assessment_tool="Lab Report #4 - Microscopy"
        )
        # Workflow service submit
        CLOWorkflowService.submit_clo_for_approval(biol_clo1_id, morgan_id)
        logger.info(f"BIOL-201 CLO 1 submitted. Status: Awaiting Approval")

        # 5. Submit ZOOL-101 CLO 1 (Rejectable)
        logger.info("Simulating ZOOL-101 submission (Patel)...")
        db.update_outcome_assessment(
            zool_clo1_id,
            students_took=0, 
            students_passed=0,
            assessment_tool="Pending tool"
        )
        CLOWorkflowService.submit_clo_for_approval(zool_clo1_id, patel_id)
        logger.info(f"ZOOL-101 CLO 1 submitted. Status: Awaiting Approval")

        # 6. Simulate Course Duplication
        logger.info("Simulating Course Duplication for BIOL-201...")
        # Check if duplicate already exists
        dup_course = db.get_course_by_number("BIOL-201-V2", institution_id)
        if not dup_course:
            dup_id = db.duplicate_course_record(biol201, overrides={"course_number": "BIOL-201-V2", "active": True})
            if dup_id:
                logger.info(f"Successfully duplicated course. New ID: {dup_id}")
            else:
                logger.error("Failed to duplicate course.")
        else:
            logger.info("Duplicate course BIOL-201-V2 already exists.")

        # 7. Trigger Reminders
        logger.info("Triggering Reminder Runbook...")
        # Use BulkEmailService directly to simulate the API/admin action
        
        # Get SQLAlchemy session
        try:
            # Access private _db_service to get sqlite session
            # This is a bit hacky but necessary for the service layer that expects a session
            session = db._db_service.sqlite.get_session()
            
            job_id = BulkEmailService.send_instructor_reminders(
                db=session,
                instructor_ids=[morgan_id, patel_id],
                created_by_user_id=admin_id,
                personal_message="Please complete your assessments by Friday.",
                term="Fall 2024"
            )
            logger.info(f"Bulk email job started: {job_id}")
            
            # Wait a moment for the background thread to work (since it's in the same process)
            time.sleep(2)
            logger.info("Reminder job processing in background...")
            
        except Exception as e:
            logger.error(f"Failed to trigger reminders: {e}")

        logger.info("Setup Complete. Ready for Demo Phase 4.")

if __name__ == "__main__":
    main()
