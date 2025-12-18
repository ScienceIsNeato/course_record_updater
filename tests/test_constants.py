"""
Test constants for generic adapter test data

Contains all test data used in E2E test fixtures, organized into dataclasses
for better readability and maintainability.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Institution:
    """Test institution data."""

    id: str
    name: str
    short_name: str
    website: str
    admin_email: str


@dataclass(frozen=True)
class Program:
    """Test program data."""

    id: str
    name: str
    short_name: str
    description: str


@dataclass(frozen=True)
class User:
    """Test user data."""

    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    display_name: str = ""


@dataclass(frozen=True)
class Course:
    """Test course data."""

    id: str
    number: str
    title: str
    department: str
    credits: str
    active: bool = True


@dataclass(frozen=True)
class Term:
    """Test term data."""

    id: str
    name: str
    display_name: str
    start_date: str
    end_date: str
    due_date: str
    active: bool = True


@dataclass(frozen=True)
class CourseOffering:
    """Test course offering data."""

    id: str
    course_id: str
    term_id: str
    status: str
    capacity: str
    enrollment: str
    section_count: str


@dataclass(frozen=True)
class CourseSection:
    """Test course section data."""

    id: str
    offering_id: str
    instructor_id: Optional[str]
    section_number: str
    enrollment: str
    status: str
    grade_distribution: str


@dataclass(frozen=True)
class CourseOutcome:
    """Test course outcome data."""

    id: str
    course_id: str
    clo_number: str
    description: str
    assessment_method: str
    assessment_data: str
    active: bool = True


# Institution
TEST_INSTITUTION = Institution(
    id="test-institution-001",
    name="Test University",
    short_name="TestU",
    website="https://testu.edu",
    admin_email="admin@testu.edu",
)

# Programs
TEST_PROGRAM_CS = Program(
    id="prog-cs",
    name="Computer Science",
    short_name="CS",
    description="Undergraduate Computer Science Program",
)

TEST_PROGRAM_MATH = Program(
    id="prog-math",
    name="Mathematics",
    short_name="MATH",
    description="Mathematics Program",
)

TEST_PROGRAM_ENG = Program(
    id="prog-eng",
    name="Engineering",
    short_name="ENG",
    description="Engineering Program",
)

# Users
TEST_ADMIN_ID = "admin-001"

TEST_INSTRUCTOR_1 = User(
    id="user-instructor-1",
    email="instructor1@testu.edu",
    first_name="Alice",
    last_name="Johnson",
    role="instructor",
)

TEST_INSTRUCTOR_2 = User(
    id="user-instructor-2",
    email="instructor2@testu.edu",
    first_name="Bob",
    last_name="Smith",
    role="instructor",
)

TEST_ADMIN_USER = User(
    id="user-admin-1",
    email="admin@testu.edu",
    first_name="Admin",
    last_name="User",
    role="institution_admin",
)

# Courses
TEST_COURSE_CS101 = Course(
    id="course-cs101",
    number="CS101",
    title="Introduction to Computer Science",
    department="Computer Science",
    credits="3",
)

TEST_COURSE_MATH201 = Course(
    id="course-math201",
    number="MATH-201",
    title="Calculus I",
    department="Mathematics",
    credits="4",
)

TEST_COURSE_ENG301 = Course(
    id="course-eng301",
    number="ENG301",
    title="Engineering Design",
    department="Engineering",
    credits="2",
)

TEST_COURSE_CS999 = Course(
    id="course-cs999",
    number="CS999",
    title="Deprecated Course",
    department="Computer Science",
    credits="3",
    active=False,
)

TEST_COURSE_MATH401 = Course(
    id="course-math401",
    number="MATH401",
    title="Advanced Topics in Mathematical Analysis and Differential Equations",
    department="Mathematics",
    credits="3",
)

TEST_COURSE_CS202 = Course(
    id="course-cs202",
    number="CS202",
    title="Data Structures & Algorithms",
    department="Computer Science",
    credits="3",
)

TEST_COURSE_CS101_DUP = Course(
    id="course-cs101-dup",
    number="CS101",
    title="Introduction to Computer Science (Duplicate)",
    department="Computer Science",
    credits="3",
)

# Terms
TEST_TERM_FA2025 = Term(
    id="term-fa2025",
    name="FA2025",
    display_name="Fall 2025",
    start_date="2025-08-26",
    end_date="2025-12-15",
    due_date="2025-12-20",
)

TEST_TERM_SP2026 = Term(
    id="term-sp2026",
    name="SP2026",
    display_name="Spring 2026",
    start_date="2026-01-13",
    end_date="2026-05-10",
    due_date="2026-05-15",
)

TEST_TERM_SU2024 = Term(
    id="term-su2024",
    name="SU2024",
    display_name="Summer 2024",
    start_date="2024-06-01",
    end_date="2024-08-15",
    due_date="2024-08-20",
    active=False,
)

# Course Offerings
TEST_OFFERING_CS101_FA2025 = CourseOffering(
    id="off-cs101-fa2025",
    course_id=TEST_COURSE_CS101.id,
    term_id=TEST_TERM_FA2025.id,
    status="active",
    capacity="75",
    enrollment="50",
    section_count="2",
)

TEST_OFFERING_MATH201_FA2025 = CourseOffering(
    id="off-math201-fa2025",
    course_id=TEST_COURSE_MATH201.id,
    term_id=TEST_TERM_FA2025.id,
    status="active",
    capacity="60",
    enrollment="45",
    section_count="1",
)

TEST_OFFERING_ENG301_SP2026 = CourseOffering(
    id="off-eng301-sp2026",
    course_id=TEST_COURSE_ENG301.id,
    term_id=TEST_TERM_SP2026.id,
    status="active",
    capacity="40",
    enrollment="30",
    section_count="1",
)

TEST_OFFERING_CS202_FA2025 = CourseOffering(
    id="off-cs202-fa2025",
    course_id=TEST_COURSE_CS202.id,
    term_id=TEST_TERM_FA2025.id,
    status="active",
    capacity="50",
    enrollment="50",
    section_count="1",
)

TEST_OFFERING_MATH401_SP2026 = CourseOffering(
    id="off-math401-sp2026",
    course_id=TEST_COURSE_MATH401.id,
    term_id=TEST_TERM_SP2026.id,
    status="active",
    capacity="30",
    enrollment="0",
    section_count="0",
)

# Course Sections
TEST_SECTION_1 = CourseSection(
    id="section-1",
    offering_id=TEST_OFFERING_CS101_FA2025.id,
    instructor_id=TEST_INSTRUCTOR_1.id,
    section_number="001",
    enrollment="25",
    status="in_progress",
    grade_distribution="{}",
)

TEST_SECTION_2 = CourseSection(
    id="section-2",
    offering_id=TEST_OFFERING_CS101_FA2025.id,
    instructor_id=TEST_INSTRUCTOR_2.id,
    section_number="002",
    enrollment="25",
    status="in_progress",
    grade_distribution='{"A":5,"B":10,"C":8,"D":2}',
)

TEST_SECTION_3 = CourseSection(
    id="section-3",
    offering_id=TEST_OFFERING_MATH201_FA2025.id,
    instructor_id=TEST_INSTRUCTOR_1.id,
    section_number="001",
    enrollment="45",
    status="in_progress",
    grade_distribution="{}",
)

TEST_SECTION_4 = CourseSection(
    id="section-4",
    offering_id=TEST_OFFERING_ENG301_SP2026.id,
    instructor_id=TEST_INSTRUCTOR_2.id,
    section_number="001",
    enrollment="30",
    status="completed",
    grade_distribution='{"A":8,"B":12,"C":7,"D":3}',
)

TEST_SECTION_5 = CourseSection(
    id="section-5",
    offering_id=TEST_OFFERING_CS202_FA2025.id,
    instructor_id=None,
    section_number="001",
    enrollment="50",
    status="assigned",
    grade_distribution="{}",
)

# Course Outcomes
TEST_OUTCOME_1 = CourseOutcome(
    id="outcome-1",
    course_id=TEST_COURSE_CS101.id,
    clo_number="1",
    description="Students will understand basic programming concepts",
    assessment_method="Written Exam",
    assessment_data="{}",
)

TEST_OUTCOME_2 = CourseOutcome(
    id="outcome-2",
    course_id=TEST_COURSE_CS101.id,
    clo_number="2",
    description="Students will write simple programs",
    assessment_method="Programming Assignment",
    assessment_data='{"students_took":25,"students_passed":20}',
)

TEST_OUTCOME_3 = CourseOutcome(
    id="outcome-3",
    course_id=TEST_COURSE_MATH201.id,
    clo_number="1",
    description="Students will solve differential equations",
    assessment_method="Problem Set",
    assessment_data="{}",
)

TEST_OUTCOME_4 = CourseOutcome(
    id="outcome-4",
    course_id=TEST_COURSE_CS101.id,
    clo_number="3",
    description="Deprecated learning outcome",
    assessment_method="Written Exam",
    assessment_data="{}",
    active=False,
)

# Assessment method constants (used as strings)
TEST_ASSESSMENT_METHOD_EXAM = "Written Exam"
TEST_ASSESSMENT_METHOD_ASSIGNMENT = "Programming Assignment"
TEST_ASSESSMENT_METHOD_PROBLEM_SET = "Problem Set"

# Grade distribution examples (JSON strings)
TEST_GRADE_DIST_EMPTY = "{}"
TEST_GRADE_DIST_SAMPLE = '{"A":5,"B":10,"C":8,"D":2}'
TEST_GRADE_DIST_COMPLETED = '{"A":8,"B":12,"C":7,"D":3}'

# Assessment data examples (JSON strings)
TEST_ASSESSMENT_DATA_EMPTY = "{}"
TEST_ASSESSMENT_DATA_SAMPLE = '{"students_took":25,"students_passed":20}'

# Timestamps
CREATED_AT = "2025-01-01T00:00:00Z"
