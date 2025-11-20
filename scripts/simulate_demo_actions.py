#!/usr/bin/env python3
"""
Simulate Demo Actions (Phase 2 & 3)

1. Invites an instructor (generating email log).
2. Creates and Imports an Excel file (generating import log).
"""

import argparse
import logging
import os
import sys
import pandas as pd
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/simulate_actions.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("simulate_actions")

def setup_env(env_name="dev"):
    db_mapping = {
        "dev": "sqlite:///course_records_dev.db",
        "e2e": "sqlite:///course_records_e2e.db",
        "prod": "sqlite:///course_records.db",
    }
    url = db_mapping.get(env_name, db_mapping["dev"])
    os.environ["DATABASE_URL"] = url
    os.environ["FLASK_ENV"] = "development"
    logger.info(f"Using database: {url}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="dev", choices=["dev", "e2e"])
    args = parser.parse_args()

    setup_env(args.env)

    # Import services AFTER env setup
    import database_service as db
    from app import app
    from invitation_service import InvitationService
    from import_service import ImportService, ConflictStrategy
    from auth_service import UserRole

    with app.app_context():
        # 1. Find Admin User
        admin = db.get_user_by_email("demo2025.admin@example.com")
        if not admin:
            logger.error("Admin user not found. Please seed database first.")
            return

        institution_id = admin.get('institution_id')
        admin_id = admin.get('user_id') or admin.get('id')

        # 2. Simulate Instructor Invitation
        logger.info("Simulating Instructor Invitation...")
        new_email = "new.faculty@demo.example.com"
        
        # Clean up if exists
        existing = db.get_user_by_email(new_email)
        if existing:
             logger.info(f"User {new_email} already exists, skipping invite.")
        else:
            try:
                invitation_data = InvitationService.create_invitation(
                    inviter_user_id=admin_id,
                    inviter_email=admin['email'],
                    invitee_email=new_email,
                    invitee_role=UserRole.INSTRUCTOR.value,
                    institution_id=institution_id,
                    personal_message="Welcome to the Biology department!"
                )
                
                if invitation_data:
                    sent = InvitationService.send_invitation(invitation_data)
                    if sent:
                        logger.info(f"Invitation sent to {new_email}")
                    else:
                        logger.error("Failed to send invitation email")
                else:
                    logger.error("Failed to create invitation record")
            except Exception as e:
                 logger.error(f"Exception inviting user: {e}")

        # 3. Simulate Course Import
        logger.info("Simulating Course Import...")
        
        # Create Excel file
        excel_path = "demo_data/course_import_template.xlsx"
        os.makedirs("demo_data", exist_ok=True)
        
        # CEI "Test" format: course, email, Term, students
        data = {
            "course": ["CHEM-101", "PHYS-101"],
            "email": ["chem.prof@demo.example.com", "phys.prof@demo.example.com"],
            "Term": ["2024 Fall", "2024 Fall"],
            "students": [25, 30]
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
                adapter_id="cei_excel_format_v1"
            )
            
            logger.info(f"Import Result: Success={result.success}, Created={result.records_created}, Updated={result.records_updated}")
            if result.errors:
                logger.error(f"Import Errors: {result.errors}")
            
        except Exception as e:
            logger.error(f"Import failed: {e}")

        logger.info("Simulation Complete.")

if __name__ == "__main__":
    main()
