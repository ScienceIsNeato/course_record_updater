"""Quick diagnostic script to check if seeded courses have program_ids."""

import database_service
from models_sql import to_dict

# Get all institutions
institutions = database_service.get_all_institutions()
print(f"\n🏢 Found {len(institutions)} institutions")

if institutions:
    cei = institutions[0]  # Assuming first is CEI
    inst_id = cei["institution_id"]
    print(f"   Institution: {cei['name']} ({inst_id})")

    # Get programs
    programs = database_service.get_programs_by_institution(inst_id)
    print(f"\n📚 Found {len(programs)} programs:")
    for prog in programs:
        print(f"   - {prog.get('name')} ({prog.get('program_id') or prog.get('id')})")

    # Get courses
    courses = database_service.get_all_courses(inst_id)
    print(f"\n📖 Found {len(courses)} courses:")
    for course in courses[:5]:  # First 5
        program_ids = course.get("program_ids", [])
        print(f"   - {course.get('course_number')}: program_ids = {program_ids}")

    if not courses[0].get("program_ids"):
        print(f"\n❌ PROBLEM: Courses don't have program_ids!")
    else:
        print(f"\n✅ Courses have program_ids populated")
