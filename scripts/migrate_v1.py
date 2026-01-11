import os
import sqlite3
import sys


def migrate(db_path: str) -> None:
    print(f"Migrating {db_path}...")
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. Add program_id to course_outcomes
    try:
        c.execute("ALTER TABLE course_outcomes ADD COLUMN program_id VARCHAR")
        print("Added program_id to course_outcomes")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("program_id already exists in course_outcomes")
        else:
            print(f"Error updating course_outcomes: {e}")

    # 2. Add program_id to course_offerings
    try:
        c.execute("ALTER TABLE course_offerings ADD COLUMN program_id VARCHAR")
        print("Added program_id to course_offerings")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("program_id already exists in course_offerings")
        else:
            print(f"Error updating course_offerings: {e}")

    # 3. Create course_section_outcomes table
    create_sql = """
    CREATE TABLE IF NOT EXISTS course_section_outcomes (
        id VARCHAR PRIMARY KEY,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        section_id VARCHAR NOT NULL,
        outcome_id VARCHAR NOT NULL,
        students_took INTEGER,
        students_passed INTEGER,
        assessment_tool VARCHAR(50),
        extras BLOB,
        FOREIGN KEY(section_id) REFERENCES course_sections(id),
        FOREIGN KEY(outcome_id) REFERENCES course_outcomes(id)
    );
    """
    try:
        c.execute(create_sql)
        print("Created course_section_outcomes table")
    except Exception as e:
        print(f"Error creating course_section_outcomes table: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "course_records.db"
    migrate(db)
