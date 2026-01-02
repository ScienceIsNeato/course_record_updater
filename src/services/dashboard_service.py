"""Dashboard data aggregation service."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.database.database_service import (
    get_active_terms,
    get_all_course_offerings,
    get_all_courses,
    get_all_institutions,
    get_all_instructors,
    get_all_sections,
    get_all_terms,
    get_all_users,
    get_course_outcomes,
    get_courses_by_program,
    get_institution_by_id,
    get_programs_by_institution,
)
from src.utils.logging_config import get_logger


class DashboardServiceError(Exception):
    """Raised when dashboard data cannot be generated."""


class DashboardService:
    """Aggregate dashboard metrics and datasets based on user scope."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def get_dashboard_data(self, user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Return dashboard data tailored to the current user's scope."""
        if not user:
            raise DashboardServiceError("Authenticated user information required")

        role = user.get("role")
        if role == "site_admin":
            payload = self._get_site_admin_data()
            scope = "system_wide"
        elif role == "program_admin":
            payload = self._get_program_admin_data(
                user.get("institution_id"), user.get("program_ids", [])
            )
            scope = "program"
        elif role == "instructor":
            payload = self._get_instructor_data(
                user.get("institution_id"),
                user.get("user_id"),
                user.get("program_ids", []),
            )
            scope = "instructor"
        elif role == "institution_admin":
            # Explicit handling for institution admins
            payload = self._get_institution_admin_data(user.get("institution_id"))
            scope = "institution"
        else:
            # Unknown roles are not allowed - fail securely
            raise ValueError(
                f"Unknown user role: {role}. Valid roles: site_admin, institution_admin, program_admin, instructor"
            )

        metadata = {
            "user_role": role,
            "data_scope": scope,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        payload.setdefault("metadata", metadata)
        payload["metadata"].update(metadata)
        return payload

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_site_admin_data(self) -> Dict[str, Any]:
        institutions = get_all_institutions() or []

        aggregated_institutions: List[Dict[str, Any]] = []
        all_programs: List[Dict[str, Any]] = []
        all_courses: List[Dict[str, Any]] = []
        all_users: List[Dict[str, Any]] = []
        all_instructors: List[Dict[str, Any]] = []
        all_sections: List[Dict[str, Any]] = []
        all_terms: List[Dict[str, Any]] = []
        system_activity: List[Dict[str, Any]] = []

        for institution in institutions:
            inst_id = institution.get("institution_id")
            inst_name = institution.get("name", "Unknown Institution")
            if not inst_id:
                continue

            programs = get_programs_by_institution(inst_id) or []
            courses = get_all_courses(inst_id) or []
            users = get_all_users(inst_id) or []
            instructors = get_all_instructors(inst_id) or []
            sections = get_all_sections(inst_id) or []
            terms = get_active_terms(inst_id) or []

            aggregated_institutions.append(
                {
                    "institution_id": inst_id,
                    "name": inst_name,
                    "user_count": len(users),
                    "program_count": len(programs),
                    "course_count": len(courses),
                }
            )

            # Add course counts to programs
            programs_with_counts = self._add_course_counts_to_programs(
                programs, courses
            )
            all_programs.extend(
                self._with_institution(programs_with_counts, inst_id, inst_name)
            )
            # Enrich courses with CLO data before adding to all_courses
            courses_with_clo = self._enrich_courses_with_clo_data(
                courses, load_clos=False
            )
            all_courses.extend(
                self._with_institution(courses_with_clo, inst_id, inst_name)
            )
            all_users.extend(self._with_institution(users, inst_id, inst_name))
            all_instructors.extend(
                self._with_institution(instructors, inst_id, inst_name)
            )
            all_sections.extend(self._with_institution(sections, inst_id, inst_name))
            all_terms.extend(self._with_institution(terms, inst_id, inst_name))

            system_activity.extend(
                self._build_activity_feed(inst_name, users, courses, sections)
            )

        summary = {
            "institutions": len(aggregated_institutions),
            "programs": len(all_programs),
            "courses": len(all_courses),
            "users": len(all_users),
            "faculty": len(
                {i.get("user_id") for i in all_instructors if i.get("user_id")}
            ),
            "sections": len(all_sections),
        }

        return {
            "summary": summary,
            "institutions": aggregated_institutions,
            "programs": all_programs,
            "courses": all_courses,
            "users": all_users,
            "instructors": all_instructors,
            "sections": all_sections,
            "terms": all_terms,
            "activity": system_activity[:25],
        }

    def _fetch_institution_raw_data(self, institution_id: str) -> Dict[str, Any]:
        """Fetch all raw data for an institution from database."""
        institution = get_institution_by_id(institution_id) or {}
        return {
            "institution": institution,
            "institution_name": institution.get("name"),
            "programs": get_programs_by_institution(institution_id) or [],
            "courses": get_all_courses(institution_id) or [],
            "users": get_all_users(institution_id) or [],
            "instructors": get_all_instructors(institution_id) or [],
            "sections": get_all_sections(institution_id) or [],
            "offerings": get_all_course_offerings(institution_id) or [],
            "offerings": get_all_course_offerings(institution_id) or [],
            "terms": get_all_terms(institution_id) or [],
        }

    def _collect_clos_from_courses(
        self,
        courses: List[Dict[str, Any]],
        program_index: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Collect all CLOs from courses, enriching them with course metadata."""
        all_clos = []
        program_index = program_index or {}

        for course in courses:
            # Resolve program name from course's program_ids
            program_name = None
            program_ids = course.get("program_ids") or []
            if program_ids:
                # Use first associated program for display context
                pid = program_ids[0]
                program = program_index.get(pid)
                if program:
                    program_name = program.get("name")

            for clo in course.get("clos", []):
                clo_copy = dict(clo)
                clo_copy["course_number"] = course.get("course_number", "")
                clo_copy["course_title"] = course.get("course_title", "")
                if program_name:
                    clo_copy["program_name"] = program_name
                all_clos.append(clo_copy)
        return all_clos

    def _build_offering_to_course_mapping(
        self, offerings: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Create offering_id -> course_id mapping."""
        offering_to_course = {}
        for offering in offerings:
            offering_id = offering.get("offering_id") or offering.get("id")
            course_id = offering.get("course_id")
            if offering_id and course_id:
                offering_to_course[offering_id] = course_id
        return offering_to_course

    def _build_institution_summary(
        self, programs: List, courses: List, users: List, faculty: List, sections: List
    ) -> Dict[str, int]:
        """Build summary statistics for institution."""
        return {
            "institutions": 1,
            "programs": len(programs),
            "courses": len(courses),
            "users": len(users),
            "faculty": len(faculty),
            "sections": len(sections),
            "students": self._total_enrollment(sections),
        }

    def _get_institution_admin_data(
        self, institution_id: Optional[str]
    ) -> Dict[str, Any]:
        if not institution_id:
            raise DashboardServiceError(
                "Institution context required for admin dashboard"
            )

        # Fetch all raw data
        raw = self._fetch_institution_raw_data(institution_id)
        institution_name = raw["institution_name"]

        # Enrich courses with CLO data
        courses = self._enrich_courses_with_clo_data(raw["courses"], load_clos=True)

        # Build indexes and mappings
        # Create program_index first so it can be used for CLO enrichment
        program_index = {self._get_program_id(p): p for p in raw["programs"]}

        # Collect CLOs with program context
        all_clos = self._collect_clos_from_courses(courses, program_index)

        course_index = self._index_by_keys(courses, ["course_id", "id"])
        faculty = self._build_faculty_directory(raw["users"], raw["instructors"])
        offering_to_course = self._build_offering_to_course_mapping(raw["offerings"])

        # Enrich sections, terms, and offerings
        sections = self._enrich_sections_with_course_data(
            raw["sections"], course_index, offering_to_course
        )
        sections = self._enrich_sections_with_instructor_data(sections, raw["users"])

        # Enrich courses with section counts (new requirement)
        courses = self._enrich_courses_with_section_counts(courses, sections)

        # Enrich terms with detailed counts (new requirement)
        terms = self._enrich_terms_with_detailed_counts(
            raw["terms"], raw["offerings"], courses, sections
        )

        offerings = self._enrich_offerings_with_section_data(raw["offerings"], sections)

        # Build metrics and aggregations
        program_metrics = self._build_program_metrics(
            raw["programs"], courses, sections, faculty
        )
        faculty_assignments = self._build_faculty_assignments(
            faculty, program_metrics, course_index, sections
        )
        summary = self._build_institution_summary(
            raw["programs"], courses, raw["users"], faculty, sections
        )

        # Build enriched result
        enriched_programs = [
            self._annotate_program(program_index, m) for m in program_metrics
        ]

        enriched: Dict[str, Any] = {
            "programs": self._with_institution(
                enriched_programs, institution_id, institution_name
            ),
            "courses": self._with_institution(
                courses, institution_id, institution_name
            ),
            "users": self._with_institution(
                raw["users"], institution_id, institution_name
            ),
            "instructors": self._with_institution(
                raw["instructors"], institution_id, institution_name
            ),
            "sections": self._with_institution(
                sections, institution_id, institution_name
            ),
            "offerings": self._with_institution(
                offerings, institution_id, institution_name
            ),
            "terms": self._with_institution(terms, institution_id, institution_name),
            "clos": self._with_institution(all_clos, institution_id, institution_name),
            "faculty": faculty,
            "faculty_assignments": faculty_assignments,
            "program_overview": program_metrics,
        }
        enriched["summary"] = summary
        enriched["institutions"] = [
            {
                "institution_id": institution_id,
                "name": institution_name,
                "user_count": len(raw["users"]),
                "program_count": len(raw["programs"]),
                "course_count": len(courses),
                "faculty_count": len(faculty),
                "section_count": len(sections),
                "student_count": summary["students"],
            }
        ]
        return enriched

    def _get_program_admin_data(
        self, institution_id: Optional[str], program_ids: List[str]
    ) -> Dict[str, Any]:
        if not institution_id:
            raise DashboardServiceError(
                "Institution context required for program admins"
            )

        # Get scoped programs for the admin
        scoped_programs = self._get_scoped_programs(institution_id, program_ids)

        # Process courses across all programs
        courses, courses_by_program = self._process_admin_program_courses(
            scoped_programs, institution_id
        )

        # Get sections and faculty data
        scoped_sections, scoped_faculty = self._get_sections_and_faculty(
            institution_id, courses, program_ids
        )

        # Build metrics and summary data
        program_metrics: List[Dict[str, Any]] = self._build_program_metrics(
            scoped_programs,
            courses,
            scoped_sections,
            scoped_faculty,
        )

        # Build final dashboard response
        return self._build_program_admin_response(
            institution_id,
            scoped_programs,
            courses,
            scoped_sections,
            scoped_faculty,
            program_metrics,
            courses_by_program,
            program_ids,
        )

    def _get_scoped_programs(
        self, institution_id: str, program_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get programs scoped to the admin's access."""
        program_ids = program_ids or []
        available_programs = get_programs_by_institution(institution_id) or []
        program_lookup = {
            self._get_program_id(program): program for program in available_programs
        }
        return [
            program_lookup.get(pid) for pid in program_ids if program_lookup.get(pid)
        ]

    def _process_admin_program_courses(
        self, scoped_programs: List[Dict[str, Any]], institution_id: str
    ) -> tuple:
        """Process courses across all programs, handling deduplication."""
        courses_dict: Dict[str, Dict[str, Any]] = (
            {}
        )  # Use dict to deduplicate by course_id
        courses_by_program: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for program in scoped_programs:
            pid = self._get_program_id(program)
            program_courses = get_courses_by_program(pid) or []

            for course in program_courses:
                enriched = self._with_program([course], program, institution_id)[0]
                course_id = self._get_course_id(enriched)

                # If course already exists, merge program_ids
                if course_id in courses_dict:
                    self._merge_course_program_ids(courses_dict[course_id], enriched)
                else:
                    courses_dict[course_id] = enriched

                courses_by_program[pid].append(enriched)

        courses = list(courses_dict.values())  # Convert back to list

        # Enrich all courses with CLO data
        courses = self._enrich_courses_with_clo_data(courses, load_clos=False)

        # Update courses_by_program with enriched data
        courses_by_program = self._rebuild_courses_by_program(courses, scoped_programs)

        return courses, courses_by_program

    def _merge_course_program_ids(
        self, existing_course: Dict[str, Any], new_course: Dict[str, Any]
    ) -> None:
        """Merge program IDs from new course into existing course."""
        existing_program_ids = set(existing_course.get("program_ids", []))
        new_program_ids = set(new_course.get("program_ids", []))
        existing_course["program_ids"] = list(existing_program_ids | new_program_ids)

    def _rebuild_courses_by_program(
        self, courses: List[Dict[str, Any]], scoped_programs: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Rebuild courses_by_program mapping with enriched course data."""
        courses_by_program = defaultdict(list)
        for course in courses:
            for program in scoped_programs:
                pid = self._get_program_id(program)
                if pid in course.get("program_ids", []):
                    courses_by_program[pid].append(course)
        return courses_by_program

    def _get_sections_and_faculty(
        self, institution_id: str, courses: List[Dict[str, Any]], program_ids: List[str]
    ) -> tuple:
        """Get sections and faculty data scoped to the programs."""
        # Get scoped sections
        all_sections = get_all_sections(institution_id) or []
        course_index = self._index_by_keys(courses, ["course_id", "id"])
        scoped_sections = [
            section
            for section in all_sections
            if self._matches_course(section, course_index)
        ]

        # Get scoped faculty
        users = get_all_users(institution_id) or []
        instructors = get_all_instructors(institution_id) or []
        faculty = self._build_faculty_directory(users, instructors)
        scoped_faculty = [
            member
            for member in faculty
            if set(member.get("program_ids") or []).intersection(program_ids)
        ]

        return scoped_sections, scoped_faculty

    def _build_program_admin_response(
        self,
        institution_id: str,
        scoped_programs: List[Dict[str, Any]],
        courses: List[Dict[str, Any]],
        scoped_sections: List[Dict[str, Any]],
        scoped_faculty: List[Dict[str, Any]],
        program_metrics: List[Dict[str, Any]],
        courses_by_program: Dict[str, List[Dict[str, Any]]],
        program_ids: List[str],
    ) -> Dict[str, Any]:
        """Build the final program admin dashboard response."""
        users = get_all_users(institution_id) or []

        summary = {
            "institutions": 1,
            "programs": len(scoped_programs),
            "courses": len(courses),
            "users": len(users),
            "faculty": len(scoped_faculty),
            "sections": len(scoped_sections),
            "students": self._total_enrollment(scoped_sections),
        }

        return {
            "summary": summary,
            "institutions": [
                {
                    "institution_id": institution_id,
                    "name": None,
                    "program_count": len(scoped_programs),
                    "course_count": len(courses),
                    "user_count": len(users),
                    "faculty_count": len(scoped_faculty),
                    "section_count": len(scoped_sections),
                    "student_count": summary["students"],
                }
            ],
            "programs": self._with_institution(scoped_programs, institution_id),
            "courses": courses,
            "users": self._with_institution(users, institution_id),
            "instructors": scoped_faculty,
            "sections": self._with_institution(scoped_sections, institution_id),
            "terms": self._with_institution(
                get_active_terms(institution_id) or [], institution_id
            ),
            "program_overview": program_metrics,
            "faculty_assignments": self._build_faculty_assignments(
                scoped_faculty,
                program_metrics,
                self._index_by_keys(courses, ["course_id", "id"]),
                scoped_sections,
            ),
            "courses_by_program": {
                pid: list(courses_by_program.get(pid, [])) for pid in program_ids
            },
        }

    def _get_instructor_data(
        self,
        institution_id: Optional[str],
        user_id: Optional[str],
        program_ids: List[str],
    ) -> Dict[str, Any]:
        if not institution_id or not user_id:
            raise DashboardServiceError(
                "Instructor dashboard requires user and institution context"
            )

        program_ids = program_ids or []
        programs = get_programs_by_institution(institution_id) or []
        program_lookup = {
            self._get_program_id(program): program for program in programs
        }
        sections = [
            section
            for section in get_all_sections(institution_id) or []
            if section.get("instructor_id") == user_id
        ]

        courses_lookup = self._index_by_keys(
            get_all_courses(institution_id) or [], ["course_id", "id"]
        )
        course_ids = {
            section.get("course_id")
            for section in sections
            if section.get("course_id") in courses_lookup
        }

        courses = []
        for cid in course_ids:
            course = courses_lookup[cid]
            program = self._resolve_program_from_course(
                course, program_lookup, program_ids
            )
            courses.append(self._with_program([course], program, institution_id)[0])

        # Enrich courses with CLO data for progress calculation
        enriched_courses = self._enrich_courses_with_clo_data(courses, load_clos=True)

        program_summaries = self._build_instructor_program_summary(
            program_lookup, enriched_courses
        )

        teaching_assignments = self._build_teaching_assignments(
            enriched_courses, sections, courses_lookup
        )
        assessment_tasks = self._build_assessment_tasks(sections, courses_lookup)

        summary = {
            "institutions": 1,
            "programs": len(program_summaries),
            "courses": len(courses),
            "users": 1,
            "sections": len(sections),
            "students": self._total_enrollment(sections),
        }

        return {
            "summary": summary,
            "institutions": [
                {
                    "institution_id": institution_id,
                    "name": None,
                    "program_count": len(program_summaries),
                    "course_count": len(courses),
                    "user_count": 1,
                    "section_count": len(sections),
                    "student_count": summary["students"],
                }
            ],
            "programs": program_summaries,
            "courses": courses,
            "users": [],
            "instructors": [],
            "sections": self._with_institution(sections, institution_id),
            "terms": self._with_institution(
                get_active_terms(institution_id) or [], institution_id
            ),
            "teaching_assignments": teaching_assignments,
            "assessment_tasks": assessment_tasks,
        }

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _with_institution(
        self,
        items: List[Dict[str, Any]],
        institution_id: str,
        institution_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        enriched = []
        for item in items:
            data = dict(item)
            data.setdefault("institution_id", institution_id)
            if institution_name is not None:
                data.setdefault("institution_name", institution_name)
            enriched.append(data)
        return enriched

    def _with_program(
        self,
        courses: List[Dict[str, Any]],
        program: Dict[str, Any],
        institution_id: str,
    ) -> List[Dict[str, Any]]:
        enriched = []
        for course in courses:
            data = dict(course)
            data.setdefault("program_id", program.get("id"))
            data.setdefault("program_name", program.get("name"))
            data.setdefault("institution_id", institution_id)
            enriched.append(data)
        return enriched

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def _index_by_keys(
        self, items: Sequence[Dict[str, Any]], candidate_keys: Sequence[str]
    ) -> Dict[Any, Dict[str, Any]]:
        index: Dict[Any, Dict[str, Any]] = {}
        for item in items:
            for key in candidate_keys:
                value = item.get(key)
                if value:
                    index[value] = dict(item)
                    break
        return index

    def _get_program_id(self, program: Optional[Dict[str, Any]]) -> Optional[str]:
        if not program:
            return None
        return program.get("program_id")

    def _get_course_id(self, course: Optional[Dict[str, Any]]) -> Optional[str]:
        if not course:
            return None
        return course.get("id") or course.get("course_id")

    def _course_program_ids(self, course: Dict[str, Any]) -> List[str]:
        program_ids = course.get("program_ids") or []
        if not program_ids:
            primary = course.get("program_id")
            if primary:
                program_ids = [primary]
        return list({pid for pid in program_ids if pid})

    def _build_faculty_directory(
        self,
        users: Sequence[Dict[str, Any]],
        instructors: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        directory: Dict[str, Dict[str, Any]] = {}

        for entry in instructors:
            user_id = entry.get("user_id") or entry.get("id")
            if not user_id:
                continue
            record = dict(entry)
            record.setdefault("user_id", user_id)
            record.setdefault("full_name", self._full_name(record))
            directory[user_id] = record

        for user in users:
            # Include institution_admin so they appear in User Management panel
            if user.get("role") not in {
                "instructor",
                "program_admin",
                "institution_admin",
            }:
                continue
            user_id = user.get("user_id") or user.get("id")
            if not user_id:
                continue
            record = dict(user)
            record.setdefault("user_id", user_id)
            record.setdefault("program_ids", record.get("program_ids") or [])
            record.setdefault("full_name", self._full_name(record))
            if user_id not in directory:
                directory[user_id] = record
            else:
                directory[user_id].update(record)

        return list(directory.values())

    def _build_program_metrics(
        self,
        programs: Sequence[Dict[str, Any]],
        courses: Sequence[Dict[str, Any]],
        sections: Sequence[Dict[str, Any]],
        faculty: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        faculty_lookup = {member.get("user_id"): member for member in faculty}
        courses_by_program = self._group_courses_by_program(courses)
        sections_by_course = self._group_sections_by_course(sections)

        metrics: List[Dict[str, Any]] = []
        for program in programs:
            program_id = self._get_program_id(program)
            if not program_id:
                continue

            program_metric = self._build_single_program_metric(
                program,
                program_id,
                courses_by_program,
                sections_by_course,
                faculty_lookup,
            )
            metrics.append(program_metric)

        return metrics

    def _group_courses_by_program(
        self, courses: Sequence[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group courses by their program IDs."""
        courses_by_program: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for course in courses:
            for program_id in self._course_program_ids(course):
                courses_by_program[program_id].append(course)
        return courses_by_program

    def _group_sections_by_course(
        self, sections: Sequence[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group sections by their course IDs."""
        sections_by_course: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for section in sections:
            course_id = section.get("course_id") or section.get("courseId")
            if course_id:
                sections_by_course[course_id].append(section)
        return sections_by_course

    def _build_single_program_metric(
        self,
        program: Dict[str, Any],
        program_id: str,
        courses_by_program: Dict[str, List[Dict[str, Any]]],
        sections_by_course: Dict[str, List[Dict[str, Any]]],
        faculty_lookup: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build metrics for a single program."""
        program_courses = courses_by_program.get(program_id, [])
        course_summaries, program_sections = self._process_program_courses(
            program_courses, sections_by_course
        )

        faculty_ids = {
            section.get("instructor_id")
            for section in program_sections
            if section.get("instructor_id")
        }
        faculty_details = [
            faculty_lookup[fid] for fid in faculty_ids if fid in faculty_lookup
        ]

        # Calculate CLO-based assessment progress
        clo_progress = self._calculate_clo_progress(program_courses)

        return {
            "program_id": program_id,
            "program_name": program.get("name") or program_id,
            "program_short_name": program.get("short_name"),
            "program_admins": program.get("program_admins", []),
            "course_count": len(course_summaries),
            "section_count": len(program_sections),
            "faculty_count": len(faculty_ids),
            "student_count": self._total_enrollment(program_sections),
            "assessment_progress": clo_progress,
            "courses": course_summaries,
            "faculty": faculty_details,
        }

    def _process_program_courses(
        self,
        program_courses: List[Dict[str, Any]],
        sections_by_course: Dict[str, List[Dict[str, Any]]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Process courses for a program, returning course summaries and all sections."""
        seen_course_ids = set()
        course_summaries = []
        program_sections: List[Dict[str, Any]] = []

        for course in program_courses:
            course_id = course.get("course_id") or course.get("id")
            if not course_id or course_id in seen_course_ids:
                continue
            seen_course_ids.add(course_id)

            course_sections = sections_by_course.get(course_id, [])
            program_sections.extend(course_sections)

            course_summaries.append(
                {
                    "course_id": course_id,
                    "course_number": course.get("course_number")
                    or course.get("number")
                    or course.get("code"),
                    "course_title": course.get("course_title")
                    or course.get("title")
                    or course.get("name"),
                    "section_count": len(course_sections),
                    "enrollment": self._total_enrollment(course_sections),
                }
            )

        return course_summaries, program_sections

    def _annotate_program(
        self,
        program_index: Dict[Optional[str], Dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        program = program_index.get(metrics.get("program_id"), {})
        annotated = dict(program) if program else {}
        annotated.setdefault("program_id", metrics.get("program_id"))
        annotated.setdefault("name", metrics.get("program_name"))
        annotated.setdefault("short_name", metrics.get("program_short_name"))
        annotated.update(
            {
                "course_count": metrics.get("course_count", 0),
                "faculty_count": metrics.get("faculty_count", 0),
                "student_count": metrics.get("student_count", 0),
                "section_count": metrics.get("section_count", 0),
                "assessment_progress": metrics.get("assessment_progress", {}),
            }
        )
        return annotated

    def _build_faculty_assignments(
        self,
        faculty: Sequence[Dict[str, Any]],
        program_metrics: Sequence[Dict[str, Any]],
        course_index: Dict[Any, Dict[str, Any]],
        sections: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        program_lookup = {metric["program_id"]: metric for metric in program_metrics}
        sections_by_instructor = self._group_sections_by_instructor(sections)

        assignments: List[Dict[str, Any]] = []
        for member in faculty:
            assignment = self._build_single_faculty_assignment(
                member, sections_by_instructor, course_index, program_lookup
            )
            if assignment:
                assignments.append(assignment)
            else:
                # Still include member in the directory even if no active assignments
                user_id = member.get("user_id")
                if user_id:
                    assignments.append(
                        {
                            "user_id": user_id,
                            "full_name": member.get("full_name")
                            or self._full_name(member),
                            "program_ids": [],
                            "course_count": 0,
                            "section_count": 0,
                            "enrollment": 0,
                            "program_summaries": [],
                            "role": member.get("role"),  # Preserve role
                        }
                    )

        return assignments

    def _group_sections_by_instructor(
        self, sections: Sequence[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group sections by instructor ID for efficient lookup."""
        sections_by_instructor: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for section in sections:
            instructor_id = section.get("instructor_id")
            if instructor_id:
                sections_by_instructor[instructor_id].append(section)
        return sections_by_instructor

    def _build_single_faculty_assignment(
        self,
        member: Dict[str, Any],
        sections_by_instructor: Dict[str, List[Dict[str, Any]]],
        course_index: Dict[Any, Dict[str, Any]],
        program_lookup: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Build assignment data for a single faculty member."""
        user_id = member.get("user_id")
        if not user_id:
            return None

        member_sections = sections_by_instructor.get(user_id, [])
        course_ids = {
            section.get("course_id") or section.get("courseId")
            for section in member_sections
            if section.get("course_id") or section.get("courseId")
        }
        if not course_ids:
            return None

        programs = self._extract_programs_from_courses(course_ids, course_index)

        return {
            "user_id": user_id,
            "full_name": member.get("full_name") or self._full_name(member),
            "program_ids": list(programs),
            "course_count": len(course_ids),
            "section_count": len(member_sections),
            "enrollment": self._total_enrollment(member_sections),
            "program_summaries": [
                program_lookup.get(pid) for pid in programs if program_lookup.get(pid)
            ],
        }

    def _extract_programs_from_courses(
        self, course_ids: set[str], course_index: Dict[Any, Dict[str, Any]]
    ) -> set[str]:
        """Extract program IDs from a set of course IDs."""
        programs: set[str] = set()
        for course_id in course_ids:
            course = course_index.get(course_id)
            if course:
                programs.update(self._course_program_ids(course))
        return programs

    def _matches_course(
        self, section: Dict[str, Any], course_index: Dict[Any, Dict[str, Any]]
    ) -> bool:
        course_id = section.get("course_id") or section.get("courseId")
        return bool(course_id and course_id in course_index)

    def _resolve_program_from_course(
        self,
        course: Dict[str, Any],
        program_lookup: Dict[Optional[str], Dict[str, Any]],
        preferred_ids: Sequence[str],
    ) -> Dict[str, Any]:
        course_program_ids = self._course_program_ids(course)
        selected_id: Optional[str] = None
        for pid in course_program_ids:
            if pid in preferred_ids:
                selected_id = pid
                break
        if not selected_id and course_program_ids:
            selected_id = course_program_ids[0]

        if selected_id and program_lookup.get(selected_id):
            return program_lookup[selected_id]
        if selected_id:
            return {"id": selected_id, "name": course.get("program_name")}
        return {"id": None, "name": None}

    def _build_instructor_program_summary(
        self,
        program_lookup: Dict[Optional[str], Dict[str, Any]],
        courses: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        summary: Dict[str, Dict[str, Any]] = {}
        for course in courses:
            program_id = course.get("program_id")
            if not program_id:
                continue
            program = program_lookup.get(program_id, {})
            if program_id not in summary:
                summary[program_id] = {
                    "program_id": program_id,
                    "program_name": program.get("name") or course.get("program_name"),
                    "course_count": 0,
                }
            summary[program_id]["course_count"] += 1
        return list(summary.values())

    def _is_clo_completed(self, clo: Dict[str, Any]) -> bool:
        """Check if a CLO is considered completed."""
        # Check if CLO has assessment data filled in
        has_took = clo.get("students_took") is not None
        has_passed = clo.get("students_passed") is not None
        has_tool = clo.get("assessment_tool") and clo.get("assessment_tool").strip()

        # Also check status for submitted/approved CLOs
        status = clo.get("status", "assigned")
        is_submitted = status in ("awaiting_approval", "approved")

        return is_submitted or (has_took and has_passed and has_tool)

    def _calculate_clo_progress(
        self, course_clos: List[Dict[str, Any]]
    ) -> tuple[int, int, float]:
        """Calculate CLO progress: total, completed, and percent complete."""
        total_clos = len(course_clos)
        completed_clos = sum(1 for clo in course_clos if self._is_clo_completed(clo))
        percent_complete = (
            round((completed_clos / total_clos) * 100, 1) if total_clos else 0
        )
        return total_clos, completed_clos, percent_complete

    def _build_teaching_assignments(
        self,
        courses: Sequence[Dict[str, Any]],
        sections: Sequence[Dict[str, Any]],
        course_index: Dict[Any, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        sections_by_course: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for section in sections:
            course_id = section.get("course_id") or section.get("courseId")
            if course_id:
                sections_by_course[course_id].append(section)

        assignments: List[Dict[str, Any]] = []
        for course in courses:
            course_id = course.get("course_id") or course.get("id")
            if not course_id:
                continue

            linked_sections = sections_by_course.get(course_id, [])
            total_clos, completed_clos, percent_complete = self._calculate_clo_progress(
                course.get("clos", [])
            )

            assignments.append(
                {
                    "course_id": course_id,
                    "course_number": course.get("course_number")
                    or course_index.get(course_id, {}).get("course_number"),
                    "course_title": course.get("course_title")
                    or course_index.get(course_id, {}).get("course_title"),
                    "section_count": len(linked_sections),
                    "enrollment": self._total_enrollment(linked_sections),
                    "sections": [dict(section) for section in linked_sections],
                    "clo_count": total_clos,
                    "clos_completed": completed_clos,
                    "percent_complete": percent_complete,
                }
            )
        return assignments

    def _build_assessment_tasks(
        self,
        sections: Sequence[Dict[str, Any]],
        course_index: Dict[Any, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []
        for section in sections:
            course_id = section.get("course_id") or section.get("courseId")
            course = course_index.get(course_id, {}) if course_id else {}
            status = section.get("status") or section.get("assessment_status")
            tasks.append(
                {
                    "section_id": section.get("section_id") or section.get("id"),
                    "section_number": section.get("section_number"),
                    "course_id": course_id,
                    "course_number": course.get("course_number")
                    or course.get("number"),
                    "course_title": course.get("course_title") or course.get("title"),
                    "due_date": section.get("assessment_due_date")
                    or section.get("due_date"),
                    "status": status or "pending",
                    "enrollment": section.get("enrollment"),
                }
            )
        return tasks

    def _calculate_clo_progress(
        self, courses: Sequence[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate assessment progress based on CLO completion."""
        total_clos = 0
        completed_clos = 0

        for course in courses:
            clos = course.get("clos", [])
            for clo in clos:
                total_clos += 1
                # A CLO is considered "completed" if it has assessment data
                assessment_data = clo.get("assessment_data", {})
                if assessment_data and isinstance(assessment_data, dict):
                    # Check if any meaningful data exists (not just an empty dict)
                    if assessment_data.get("students_took") or assessment_data.get(
                        "students_passed"
                    ):
                        completed_clos += 1

        percent = round((completed_clos / total_clos) * 100, 1) if total_clos else 0
        return {
            "completed": completed_clos,
            "total": total_clos,
            "percent_complete": percent,
        }

    def _calculate_progress(self, sections: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Legacy method for section-based progress (deprecated)."""
        if not sections:
            return {"completed": 0, "total": 0, "percent_complete": 0}

        completed = sum(
            1
            for section in sections
            if (section.get("status") or "").lower() in {"completed", "done"}
        )
        total = len(sections)
        percent = round((completed / total) * 100, 1) if total else 0
        return {
            "completed": completed,
            "total": total,
            "percent_complete": percent,
        }

    def _total_enrollment(self, sections: Sequence[Dict[str, Any]]) -> int:
        total = 0
        for section in sections:
            enrollment = section.get("enrollment")
            if enrollment is not None:
                try:
                    total += int(enrollment)
                except (ValueError, TypeError):
                    continue
        return total

    def _build_activity_feed(
        self,
        institution_name: Optional[str],
        users: Sequence[Dict[str, Any]],
        courses: Sequence[Dict[str, Any]],
        sections: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        feed: List[Dict[str, Any]] = []
        timestamp = datetime.now(timezone.utc).isoformat()

        # System activities should be attributed to SITE_ADMIN user
        from src.utils.constants import SYSTEM_USER_NAME

        system_user = SYSTEM_USER_NAME

        for course in courses[:5]:
            feed.append(
                {
                    "timestamp": timestamp,
                    "institution": institution_name,
                    "user": system_user,
                    "action": "Course Synced",
                    "details": course.get("course_number") or course.get("name"),
                }
            )
        for section in sections[:5]:
            # Replace GUID with meaningful identifier
            section_detail = (
                section.get("course_number") or section.get("course_id") or "Section"
            )
            feed.append(
                {
                    "timestamp": timestamp,
                    "institution": institution_name,
                    "user": system_user,
                    "action": "Section Update",
                    "details": section_detail,
                }
            )
        for user in users[:5]:
            feed.append(
                {
                    "timestamp": timestamp,
                    "institution": institution_name,
                    "user": self._full_name(user) or user.get("email"),
                    "action": "User Activity",
                    "details": user.get("role"),
                }
            )
        return feed

    def _build_assessment_progress(
        self, sections: Sequence[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return self._calculate_progress(sections)

    def _full_name(self, data: Dict[str, Any]) -> str:
        first = data.get("first_name") or ""
        last = data.get("last_name") or ""
        name = f"{first} {last}".strip()
        return name or data.get("full_name") or ""

    def _add_course_counts_to_programs(
        self, programs: List[Dict[str, Any]], courses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Add course_count to each program based on courses that reference the program.

        Args:
            programs: List of program dictionaries
            courses: List of course dictionaries

        Returns:
            List of programs with course_count added
        """
        programs_with_counts = []

        for program in programs:
            program_copy = program.copy()
            program_id = program.get("id", program.get("program_id"))

            # Count courses that have this program in their program_ids
            course_count = 0
            if program_id:
                for course in courses:
                    program_ids = course.get("program_ids", [])
                    if program_id in program_ids:
                        course_count += 1

            program_copy["course_count"] = course_count
            programs_with_counts.append(program_copy)

        return programs_with_counts

    def _enrich_courses_with_clo_data(
        self, courses: List[Dict[str, Any]], load_clos: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Enrich courses with CLO (Course Learning Outcomes) data.

        Args:
            courses: List of course dictionaries
            load_clos: Whether to actually load CLO data (for performance optimization)

        Returns:
            List of courses with clo_count added
        """
        enriched_courses = []

        for course in courses:
            course_copy = course.copy()
            course_id = course.get("course_id", course.get("id"))

            if course_id and load_clos:
                try:
                    # Get CLOs for this course
                    clos = get_course_outcomes(course_id)
                    course_copy["clo_count"] = len(clos) if clos else 0
                    course_copy["clos"] = clos  # Include full CLO data for frontend
                except Exception as e:
                    self.logger.warning(
                        f"Failed to fetch CLOs for course {course_id}: {e}"
                    )
                    course_copy["clo_count"] = 0
                    course_copy["clos"] = []
            else:
                # For performance optimization, skip CLO loading
                course_copy["clo_count"] = 0
                course_copy["clos"] = []

            enriched_courses.append(course_copy)

        return enriched_courses

    def _enrich_sections_with_course_data(
        self,
        sections: List[Dict[str, Any]],
        course_index: Dict[str, Dict[str, Any]],
        offering_to_course: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Enrich sections with course number and title from course index.

        Sections have offering_id, which maps to course_id via offerings.

        Args:
            sections: List of section dictionaries
            course_index: Dictionary mapping course_id to course data
            offering_to_course: Dictionary mapping offering_id to course_id

        Returns:
            List of sections enriched with course_number and course_title
        """
        return [
            self._enrich_single_section(i, section, course_index, offering_to_course)
            for i, section in enumerate(sections)
        ]

    def _enrich_sections_with_instructor_data(
        self,
        sections: List[Dict[str, Any]],
        users: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Enrich sections with instructor name and email.

        Args:
            sections: List of section dictionaries
            users: List of all users (to lookup instructor details)

        Returns:
            List of sections enriched with instructor_name and instructor_email
        """
        # Build instructor lookup by user_id
        instructor_lookup = {}
        for user in users:
            user_id = user.get("user_id") or user.get("id")
            if user_id:
                instructor_lookup[user_id] = {
                    "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                    or user.get("email", ""),
                    "email": user.get("email", ""),
                }

        # Enrich sections
        enriched_sections = []
        for section in sections:
            section_copy = section.copy()
            instructor_id = section.get("instructor_id")

            if instructor_id and instructor_id in instructor_lookup:
                instructor = instructor_lookup[instructor_id]
                section_copy["instructor_name"] = instructor["name"]
                section_copy["instructor_email"] = instructor["email"]

            enriched_sections.append(section_copy)

        return enriched_sections

    def _enrich_terms_with_offering_counts(
        self,
        terms: List[Dict[str, Any]],
        offerings: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Enrich terms with the count of offerings for each term.

        Args:
            terms: List of term dictionaries
            offerings: List of offering dictionaries

        Returns:
            List of terms enriched with offering_count
        """
        # Build a count of offerings per term
        offering_counts: Dict[str, int] = {}
        for offering in offerings:
            term_id = offering.get("term_id")
            if term_id:
                offering_counts[term_id] = offering_counts.get(term_id, 0) + 1

        # Add counts to terms
        enriched_terms = []
        for term in terms:
            term_id = term.get("term_id") or term.get("id")
            enriched_term = dict(term)
            enriched_term["offering_count"] = offering_counts.get(term_id, 0)
            enriched_terms.append(enriched_term)

        return enriched_terms

    def _build_term_section_counts(
        self, offerings: List[Dict[str, Any]], sections: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Build a mapping of term_id to section count."""
        offering_term_map = {
            o.get("offering_id"): o.get("term_id")
            for o in offerings
            if o.get("offering_id")
        }

        term_section_counts: Dict[str, int] = {}
        for section in sections:
            offering_id = section.get("offering_id")
            term_id = offering_term_map.get(offering_id)
            if term_id:
                term_section_counts[term_id] = term_section_counts.get(term_id, 0) + 1

        return term_section_counts

    def _extract_program_ids_from_offering(
        self,
        offering: Dict[str, Any],
        course_lookup: Dict[str, Dict[str, Any]],
    ) -> set:
        """Extract all program IDs associated with an offering."""
        program_ids = set()

        # Get program from offering first
        if offering.get("program_id"):
            program_ids.add(offering["program_id"])

        # Fallback to course if no program on offering
        course_id = offering.get("course_id")
        if course_id and course_id in course_lookup:
            course = course_lookup[course_id]

            # Handle program_ids list
            p_ids = course.get("program_ids", [])
            if isinstance(p_ids, list):
                program_ids.update(p_ids)
            elif isinstance(p_ids, str):
                program_ids.add(p_ids)

            # Handle legacy program_id field
            if course.get("program_id"):
                program_ids.add(course["program_id"])

        return program_ids

    def _enrich_terms_with_detailed_counts(
        self,
        terms: List[Dict[str, Any]],
        offerings: List[Dict[str, Any]],
        courses: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Enrich terms with detailed counts: programs, courses, sections.

        Args:
            terms: List of term dictionaries
            offerings: List of offering dictionaries
            courses: List of course dictionaries
            sections: List of section dictionaries

        Returns:
            List of terms enriched with program_count, course_count, section_count.
        """
        course_lookup = {c.get("course_id") or c.get("id"): c for c in courses}

        # Group offerings by term
        term_offerings: Dict[str, List[Dict[str, Any]]] = {}
        for offering in offerings:
            term_id = offering.get("term_id")
            if term_id:
                term_offerings.setdefault(term_id, []).append(offering)

        term_section_counts = self._build_term_section_counts(offerings, sections)

        enriched_terms = []
        for term in terms:
            term_id = term.get("term_id") or term.get("id")
            term_copy = dict(term)
            term_specific_offerings = term_offerings.get(term_id, [])

            # Calculate unique programs and courses
            unique_program_ids = set()
            unique_course_ids = set()

            for offering in term_specific_offerings:
                unique_program_ids.update(
                    self._extract_program_ids_from_offering(offering, course_lookup)
                )
                if offering.get("course_id"):
                    unique_course_ids.add(offering["course_id"])

            term_copy["program_count"] = len(unique_program_ids)
            term_copy["course_count"] = len(unique_course_ids)
            term_copy["offering_count"] = len(term_specific_offerings)
            term_copy["section_count"] = term_section_counts.get(term_id, 0)

            enriched_terms.append(term_copy)

        return enriched_terms

    def _enrich_courses_with_section_counts(
        self,
        courses: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Add section_count to each course."""
        # Map course_id -> section count
        course_section_counts: Dict[str, int] = {}

        # We need to map section -> offering -> course
        # Sections already enriched with course_id in _enrich_sections_with_course_data
        for section in sections:
            course_id = section.get("course_id")
            if course_id:
                course_section_counts[course_id] = (
                    course_section_counts.get(course_id, 0) + 1
                )

        enriched_courses = []
        for course in courses:
            course_copy = course.copy()
            c_id = course.get("course_id") or course.get("id")
            course_copy["section_count"] = course_section_counts.get(c_id, 0)
            enriched_courses.append(course_copy)

        return enriched_courses

    def _enrich_offerings_with_section_data(
        self,
        offerings: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Enrich offerings with section count and total enrollment.

        Args:
            offerings: List of offering dictionaries
            sections: List of section dictionaries

        Returns:
            List of offerings enriched with section_count and total_enrollment
        """
        offering_data = self._build_offering_section_rollup(sections)
        return [
            self._apply_offering_section_rollup(offering, offering_data)
            for offering in offerings
        ]

    def _build_offering_section_rollup(
        self, sections: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, int]]:
        """Build section_count/total_enrollment rollups keyed by offering_id."""
        offering_data: Dict[str, Dict[str, int]] = {}
        for section in sections:
            offering_id = section.get("offering_id")
            if not offering_id:
                continue
            entry = offering_data.setdefault(
                offering_id, {"section_count": 0, "total_enrollment": 0}
            )
            entry["section_count"] += 1
            entry["total_enrollment"] += self._safe_int(
                section.get("enrollment"), section.get("section_id")
            )
        return offering_data

    def _apply_offering_section_rollup(
        self,
        offering: Dict[str, Any],
        offering_data: Dict[str, Dict[str, int]],
    ) -> Dict[str, Any]:
        """Apply rollup counts to a single offering (defaults to 0/0 when missing)."""
        offering_id = offering.get("offering_id") or offering.get("id")
        enriched_offering = dict(offering)
        rollup = offering_data.get(offering_id) if offering_id else None
        enriched_offering["section_count"] = rollup["section_count"] if rollup else 0
        enriched_offering["total_enrollment"] = (
            rollup["total_enrollment"] if rollup else 0
        )
        return enriched_offering

    def _safe_int(self, value: Any, context_id: Any = None) -> int:
        """Convert value to int; log and return 0 if invalid."""
        if value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            self.logger.warning(
                f"Invalid enrollment value for section {context_id}: {value}"
            )
            return 0

    def _enrich_single_section(
        self,
        index: int,
        section: Dict[str, Any],
        course_index: Dict[str, Dict[str, Any]],
        offering_to_course: Dict[str, str],
    ) -> Dict[str, Any]:
        """Enrich a single section with course data."""
        section_copy = section.copy()
        offering_id = section.get("offering_id")
        course_id = offering_to_course.get(offering_id) if offering_id else None

        if course_id and course_id in course_index:
            # Success: add course data
            course = course_index[course_id]
            section_copy["course_number"] = course.get("course_number", "")
            section_copy["course_title"] = course.get("course_title", "")
            section_copy["course_id"] = course_id
        else:
            # Failure: log and add empty defaults
            self._log_enrichment_failure(
                index, offering_id, course_id, offering_to_course, course_index
            )
            section_copy.setdefault("course_number", "")
            section_copy.setdefault("course_title", "")

        return section_copy

    def _log_enrichment_failure(
        self,
        index: int,
        offering_id: Optional[str],
        course_id: Optional[str],
        offering_to_course: Dict[str, str],
        course_index: Dict[str, Dict[str, Any]],
    ) -> None:
        """Log section enrichment failures (first 3 only to avoid spam)."""
        if index >= 3:
            return

        in_offering_map = offering_id in offering_to_course if offering_id else False
        in_course_index = course_id in course_index if course_id else False

        self.logger.warning(
            f"[SECTION ENRICHMENT] Failed to enrich section {index}: "
            f"offering_id={offering_id}, course_id={course_id}, "
            f"in_offering_map={in_offering_map}, in_course_index={in_course_index}"
        )


def build_dashboard_service() -> DashboardService:
    """Factory for dependency injection in tests."""
    return DashboardService()
