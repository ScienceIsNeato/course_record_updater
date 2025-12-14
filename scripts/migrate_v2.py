import sqlite3
import os
import sys

def migrate(db_path):
    print(f"Migrating {db_path} (v2)...")
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    columns = [
        ("status", "VARCHAR DEFAULT 'assigned'"),
        ("approval_status", "VARCHAR DEFAULT 'pending'"),
        ("submitted_at", "DATETIME"),
        ("submitted_by", "VARCHAR"),
        ("reviewed_at", "DATETIME"),
        ("reviewed_by", "VARCHAR"),
        ("feedback_comments", "TEXT")
    ]

    for col_name, col_type in columns:
        try:
            c.execute(f"ALTER TABLE course_section_outcomes ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name} to course_section_outcomes")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists")
            elif "no such table" in str(e).lower():
                print("Table course_section_outcomes does not exist (run v1 first)")
                break
            else:
                print(f"Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Migration v2 complete.")

if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "course_records.db"
    migrate(db)
