"""Support mixin for dashboard aggregation helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, cast

from src.utils.time_utils import get_current_time


class DashboardServiceSupportMixin:
    def _with_institution(
        self,
        items: List[Dict[str, Any]],
        institution_id: str,
        institution_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []
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
        enriched: List[Dict[str, Any]] = []
        for course in courses:
            data = dict(course)
            data.setdefault("program_id", program.get("id"))
            data.setdefault("program_name", program.get("name"))
            data.setdefault("institution_id", institution_id)
            enriched.append(data)
        return enriched

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
        program_id = program.get("program_id") or program.get("id")
        return str(program_id) if program_id else None

    def _get_course_id(self, course: Optional[Dict[str, Any]]) -> Optional[str]:
        if not course:
            return None
        course_id = course.get("id") or course.get("course_id")
        return str(course_id) if course_id else None

    def _course_program_ids(self, course: Dict[str, Any]) -> List[str]:
        program_ids: List[str] = []
        raw_program_ids = course.get("program_ids")
        if isinstance(raw_program_ids, list):
            program_id_values: List[Any] = cast(List[Any], raw_program_ids)
            program_ids = [
                str(program_id) for program_id in program_id_values if program_id
            ]
        elif isinstance(raw_program_ids, str):
            program_ids = [raw_program_ids]

        if not program_ids:
            primary = course.get("program_id")
            if primary:
                program_ids = [str(primary)]

        return list(dict.fromkeys(program_ids))

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
            user_id_str = str(user_id)
            record = dict(entry)
            record.setdefault("user_id", user_id_str)
            record.setdefault("full_name", self._full_name(record))
            directory[user_id_str] = record

        for user in users:
            if user.get("role") not in {
                "instructor",
                "program_admin",
                "institution_admin",
            }:
                continue

            user_id = user.get("user_id") or user.get("id")
            if not user_id:
                continue

            user_id_str = str(user_id)
            record = dict(user)
            record.setdefault("user_id", user_id_str)
            record.setdefault("program_ids", record.get("program_ids") or [])
            record.setdefault("full_name", self._full_name(record))
            if user_id_str not in directory:
                directory[user_id_str] = record
            else:
                directory[user_id_str].update(record)

        return list(directory.values())

    def _build_program_metrics(
        self,
        programs: Sequence[Dict[str, Any]],
        courses: Sequence[Dict[str, Any]],
        sections: Sequence[Dict[str, Any]],
        faculty: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        faculty_lookup: Dict[str, Dict[str, Any]] = {}
        for member in faculty:
            member_id = member.get("user_id")
            if not member_id:
                continue
            faculty_lookup[member_id] = member
        courses_by_program = self._group_courses_by_program(courses)
        sections_by_course = self._group_sections_by_course(sections)

        metrics: List[Dict[str, Any]] = []
        for program in programs:
            program_id = self._get_program_id(program)
            if not program_id:
                continue

            metrics.append(
                self._build_single_program_metric(
                    program,
                    program_id,
                    courses_by_program,
                    sections_by_course,
                    faculty_lookup,
                )
            )

        return metrics

    def _group_courses_by_program(
        self, courses: Sequence[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        courses_by_program: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for course in courses:
            for program_id in self._course_program_ids(course):
                courses_by_program[program_id].append(course)
        return courses_by_program

    def _group_sections_by_course(
        self, sections: Sequence[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
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

        return {
            "program_id": program_id,
            "program_name": program.get("name") or program_id,
            "program_short_name": program.get("short_name"),
            "program_admins": program.get("program_admins", []),
            "course_count": len(course_summaries),
            "section_count": len(program_sections),
            "faculty_count": len(faculty_ids),
            "student_count": self._total_enrollment(program_sections),
            "assessment_progress": self._calculate_clo_progress(program_courses),
            "courses": course_summaries,
            "faculty": faculty_details,
        }

    def _process_program_courses(
        self,
        program_courses: List[Dict[str, Any]],
        sections_by_course: Dict[str, List[Dict[str, Any]]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        seen_course_ids: set[str] = set()
        course_summaries: List[Dict[str, Any]] = []
        program_sections: List[Dict[str, Any]] = []

        for course in program_courses:
            course_id_value = course.get("course_id") or course.get("id")
            if not course_id_value:
                continue
            course_id = str(course_id_value)
            if course_id in seen_course_ids:
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
        program_index: Dict[str, Dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        program_id = str(metrics.get("program_id") or "")
        program = program_index.get(program_id, {})
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
                continue

            user_id = member.get("user_id")
            if user_id:
                assignments.append(
                    {
                        "user_id": user_id,
                        "full_name": member.get("full_name") or self._full_name(member),
                        "program_ids": [],
                        "course_count": 0,
                        "section_count": 0,
                        "enrollment": 0,
                        "program_summaries": [],
                        "role": member.get("role"),
                    }
                )

        return assignments

    def _group_sections_by_instructor(
        self, sections: Sequence[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
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
        user_id = member.get("user_id")
        if not user_id:
            return None

        member_sections = sections_by_instructor.get(user_id, [])
        course_ids = {
            section.get("course_id") or section.get("courseId")
            for section in member_sections
            if section.get("course_id") or section.get("courseId")
        }
        str_course_ids = {str(course_id) for course_id in course_ids if course_id}
        if not str_course_ids:
            return None

        programs = self._extract_programs_from_courses(str_course_ids, course_index)
        return {
            "user_id": user_id,
            "full_name": member.get("full_name") or self._full_name(member),
            "program_ids": list(programs),
            "course_count": len(course_ids),
            "section_count": len(member_sections),
            "enrollment": self._total_enrollment(member_sections),
            "program_summaries": [
                program_lookup.get(program_id)
                for program_id in programs
                if program_lookup.get(program_id)
            ],
        }

    def _extract_programs_from_courses(
        self, course_ids: set[str], course_index: Dict[Any, Dict[str, Any]]
    ) -> set[str]:
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
        for program_id in course_program_ids:
            if program_id in preferred_ids:
                selected_id = program_id
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
        has_took = clo.get("students_took") is not None
        has_passed = clo.get("students_passed") is not None
        assessment_tool = clo.get("assessment_tool")
        has_tool = bool(assessment_tool and assessment_tool.strip())
        status = clo.get("status", "assigned")
        is_submitted = status in ("awaiting_approval", "approved")
        return is_submitted or (has_took and has_passed and has_tool)

    def _calculate_course_clo_metrics(
        self,
        course_clos: List[Dict[str, Any]],
        linked_sections: Sequence[Dict[str, Any]],
    ) -> tuple[int, int, float]:
        total_clos = len(course_clos)
        completed_clos = sum(1 for clo in course_clos if self._is_clo_completed(clo))
        percent_complete = (
            round((completed_clos / total_clos) * 100, 1) if total_clos else 0
        )
        course_fields_complete = all(
            section.get("students_passed") is not None
            and section.get("students_dfic") is not None
            for section in linked_sections
        )
        if percent_complete == 100 and not course_fields_complete:
            percent_complete = 99.0
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
            total_clos, completed_clos, percent_complete = (
                self._calculate_course_clo_metrics(
                    course.get("clos", []), linked_sections
                )
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
        total_clos = 0
        completed_clos = 0
        for course in courses:
            for clo in course.get("clos", []):
                total_clos += 1
                if self._is_clo_completed(clo):
                    completed_clos += 1

        percent = round((completed_clos / total_clos) * 100, 1) if total_clos else 0
        return {
            "completed": completed_clos,
            "total": total_clos,
            "percent_complete": percent,
        }

    def _calculate_progress(self, sections: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
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
            if enrollment is None:
                continue
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
        timestamp = get_current_time().isoformat()
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
