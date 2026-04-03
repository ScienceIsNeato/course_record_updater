#!/usr/bin/env python3
"""Database seeding script for LoopCloser.

SECURITY: This script only works with LOCAL databases (sqlite:// or localhost).
For remote/deployed databases, use scripts/seed_remote_db.sh which has proper
safeguards and confirmation prompts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Typing imports for static analysis
from typing import Any, Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.demo_seed_profiles import DEMO_STORY_PROFILES, DEMO_TERM_CONTEXT
from scripts.seed_db_baseline import BaselineSeeder
from src.database import database_service
from src.services.password_service import hash_password


class BaselineTestSeeder(BaselineSeeder):
    """
    Seeds baseline test infrastructure for E2E/integration tests.

    Uses tests/fixtures/baseline_test_manifest.json for all data.
    All data must come from manifest - no hardcoded fallbacks.
    """

    DEFAULT_MANIFEST_PATH = "tests/fixtures/baseline_test_manifest.json"

    def __init__(self, manifest_path: Optional[str] = None) -> None:
        super().__init__()
        self.manifest_path = manifest_path

    def seed(self) -> bool:
        """Implementation of abstract seed method"""
        return self.seed_baseline()

    def _get_manifest_path(self) -> str:
        """Get the manifest path, relative to project root"""
        if self.manifest_path:
            return self.manifest_path

        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        return os.path.join(project_root, self.DEFAULT_MANIFEST_PATH)

    def _extract_instructor_ids(
        self, manifest_data: Dict[str, Any], user_ids: List[Optional[str]]
    ) -> List[str]:
        """Extract instructor IDs from created users."""
        instructor_ids: List[str] = []
        for i, user_data in enumerate(manifest_data["users"]):
            if user_data.get("role") != "instructor":
                continue
            if i >= len(user_ids) or user_ids[i] is None:
                continue
            instructor_ids.append(user_ids[i])  # type: ignore[arg-type]
        return instructor_ids

    def _prepare_offerings_data(
        self, offerings_data: List[Dict[str, Any]], term_ids: List[str]
    ) -> str:
        """Prepare offerings data with course codes and term IDs. Returns default term ID."""
        for offering in offerings_data:
            course_idx = offering.get("course_idx", 0)
            offering["course_code"] = str(course_idx)
            term_idx = offering.get("term_idx", 0)
            if term_idx < len(term_ids):
                offering["_term_id"] = term_ids[term_idx]
        return term_ids[1] if len(term_ids) > 1 else term_ids[0]

    def seed_baseline(self, manifest_data: Optional[Dict[str, Any]] = None) -> bool:
        """Seed baseline data from manifest - REQUIRED"""
        self.log("🌱 Seeding baseline E2E infrastructure...")

        # Refresh database service to ensure it uses the correct database
        # NOTE: Must use database_service.refresh_connection() NOT database_factory.refresh_database_service()
        # because the latter only updates the factory cache, not the database_service.db alias
        from src.database import database_service

        database_service.refresh_connection()

        # Load manifest - REQUIRED
        if manifest_data is None:
            manifest_path = self._get_manifest_path()
            manifest_data = self.load_manifest(manifest_path)

        if not manifest_data:
            self.log("❌ Manifest is required for baseline seeding")
            return False

        # Validate required sections
        required_sections = [
            "institutions",
            "programs",
            "terms",
            "courses",
            "users",
            "offerings",
        ]
        if not self._validate_required_manifest_sections(
            manifest_data, required_sections
        ):
            return False

        # Create institutions
        self.log("🏢 Creating test institutions...")
        inst_ids = self.create_institutions_from_manifest(manifest_data["institutions"])

        # Create programs
        self.log("📚 Creating academic programs...")
        prog_ids = self.create_programs_from_manifest(
            inst_ids, manifest_data["programs"]
        )

        # Build program_map: code -> ID (for manifests using program_code)
        program_map = self._build_program_map(manifest_data["programs"], prog_ids)

        # Create terms
        self.log("📅 Creating academic terms...")
        term_ids = self.create_terms_from_manifest(inst_ids, manifest_data["terms"])

        # Create courses - pass program_map for code-based lookups, or prog_ids for idx-based
        self.log("📖 Creating sample courses...")
        # Use program_map if any course uses program_code, else fall back to list
        uses_program_code = any(
            "program_code" in c for c in manifest_data.get("courses", [])
        )
        program_ref = program_map if uses_program_code and program_map else prog_ids
        course_ids = self.create_courses_from_manifest(
            inst_ids, manifest_data["courses"], program_ref
        )

        # Build course_map by index for offerings
        course_map = {str(i): cid for i, cid in enumerate(course_ids)}

        # Create users and extract instructor IDs for section assignment
        user_ids, instructor_ids = self._create_baseline_users(
            manifest_data, inst_ids, prog_ids, program_map
        )

        # Create offerings and sections
        self.log("📝 Creating course offerings and sections...")
        offerings_data = manifest_data["offerings"]
        default_term_id = self._prepare_offerings_data(offerings_data, term_ids)

        result = self.create_offerings_from_manifest(
            institution_id=inst_ids[0],
            term_id_or_map=default_term_id,
            offerings_data=offerings_data,
            course_map=course_map,
            instructor_ids=instructor_ids,
        )
        self.log(
            f"   ✓ Created {len(result['offering_ids'])} offerings and {result['section_count']} sections"
        )

        self.log("✅ Baseline seeding completed!")
        self.print_summary()
        return True

    def _create_baseline_users(
        self,
        manifest_data: Dict[str, Any],
        inst_ids: List[str],
        prog_ids: List[str],
        program_map: Dict[str, str],
    ) -> tuple[List[Optional[str]], List[str]]:
        """Create users from manifest and extract instructor IDs."""
        self.log("👥 Creating users...")
        from src.utils.constants import GENERIC_PASSWORD

        default_hash = hash_password(GENERIC_PASSWORD)
        uses_program_code_users = any(
            "program_code" in u for u in manifest_data.get("users", [])
        )
        user_program_ref = (
            program_map if uses_program_code_users and program_map else prog_ids
        )
        user_ids = self.create_users_from_manifest(
            inst_ids, manifest_data["users"], user_program_ref, default_hash
        )
        instructor_ids = self._extract_instructor_ids(manifest_data, user_ids)
        return user_ids, instructor_ids

    def print_summary(self) -> None:
        """Print seeding summary"""
        self.log("")
        self.log("📊 Summary:")
        self.log(f"   Institutions: {len(self.created['institutions'])} created")
        self.log(f"   Users: {len(self.created['users'])} created")
        self.log(f"   Programs: {len(self.created['programs'])} created")
        self.log(f"   Terms: {len(self.created['terms'])} created")
        self.log(f"   Courses: {len(self.created['courses'])} created")
        self.log("")
        self.log("🔑 Test Accounts: (see manifest for credentials)")


class DatabaseSeeder:
    """
    Compatibility wrapper for integration tests.

    Integration tests expect DatabaseSeeder.seed_full_dataset() but we refactored
    to BaselineTestSeeder.seed_baseline() for E2E tests. This provides backward compatibility.
    """

    def __init__(self, verbose: bool = True) -> None:
        self.seeder = BaselineTestSeeder()
        self.verbose = verbose

    def seed_full_dataset(self) -> bool:
        """Seed the full baseline dataset (compatibility method)"""
        return self.seeder.seed_baseline()


class DemoSeeder(BaselineSeeder):
    """
    Complete seeding for product demonstrations (2025).

    Uses demos/full_semester_manifest.json for all data configuration.
    Extends BaselineSeeder and uses its generic manifest methods.
    """

    DEFAULT_MANIFEST_PATH = "demos/full_semester_manifest.json"
    NEON_SEEDED_MSG = "   1. Database seeded on Neon - app will see changes immediately"
    LOGIN_WITH_DEMO_CREDENTIALS_MSG = "   3. Login with demo credentials"

    def __init__(self, manifest_path: Optional[str] = None, env: str = "dev") -> None:
        super().__init__()
        self.manifest_path = manifest_path
        self.env = env
        self._manifest_cache: Optional[Dict[str, Any]] = None

    def seed(self) -> bool:
        """Implementation of abstract seed method - calls seed_demo()"""
        return self.seed_demo()

    def log(self, message: str) -> None:
        """Log with [SEED] prefix"""
        print(f"[SEED] {message}")

    def load_demo_manifest(self) -> Dict[str, Any]:
        """Load demo data from external JSON (cached)"""
        if self._manifest_cache is not None:
            return self._manifest_cache

        try:
            if self.manifest_path:
                manifest_path = os.path.abspath(self.manifest_path)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                manifest_path = os.path.join(
                    script_dir, "..", self.DEFAULT_MANIFEST_PATH
                )

            if os.path.exists(manifest_path):
                self.log(f"📋 Loading demo data from {manifest_path}")
                with open(manifest_path, "r") as f:
                    self._manifest_cache = json.load(f)
                    return self._manifest_cache
            else:
                self.log(f"⚠️  Manifest not found at {manifest_path}, using defaults")
                self._manifest_cache = {}
                return {}
        except Exception as e:
            self.log(f"⚠️  Failed to load manifest: {e}")
            self._manifest_cache = {}
            return {}

    def _build_demo_reference_maps(
        self,
        manifest: Dict[str, Any],
        term_ids: List[str],
        course_ids: List[str],
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        """Build term and course lookup maps for offering creation."""
        term_map: Dict[str, str] = {}
        for index, term in enumerate(manifest["terms"]):
            if index < len(term_ids):
                term_map[term.get("term_code") or term.get("code")] = term_ids[index]

        course_map: Dict[str, str] = {}
        for index, course in enumerate(manifest["courses"]):
            target_code = course.get("code") or course.get("course_number")
            if target_code and index < len(course_ids):
                course_map[target_code] = course_ids[index]

        return term_map, course_map

    def seed_demo(self) -> bool:
        """Seed complete data for product demo - manifest required."""
        self.log("🎬 Seeding demo environment...")

        # Load manifest - REQUIRED
        manifest = self.load_demo_manifest()
        if not manifest:
            self.log("❌ Manifest is required for demo seeding")
            return False

        # Validate required sections
        required = [
            "institutions",
            "programs",
            "terms",
            "courses",
            "users",
            "offerings",
        ]
        if not self._validate_required_manifest_sections(
            manifest, required, require_non_empty=True
        ):
            return False

        # 1. Create Institutions
        self.log("🏢 Creating demo institution(s)...")
        inst_ids = self.create_institutions_from_manifest(manifest["institutions"])
        if not inst_ids:
            return False

        # 2. Create Programs
        self.log("📚 Creating demo programs...")
        prog_ids = self.create_programs_from_manifest(inst_ids, manifest["programs"])

        # Build map
        program_map = self._build_program_map(manifest["programs"], prog_ids)

        # 3. Create Terms
        self.log("📅 Creating terms...")
        term_ids = self.create_terms_from_manifest(inst_ids, manifest["terms"])

        # 4. Create Courses
        self.log("📖 Creating demo courses...")
        course_ids = self.create_courses_from_manifest(
            inst_ids, manifest["courses"], program_map
        )
        term_map, course_map = self._build_demo_reference_maps(
            manifest, term_ids, course_ids
        )

        # 5. Create CLOs
        self.log("🎯 Creating Course Learning Outcomes...")
        clo_count = self.create_clos_from_manifest(course_ids, manifest)
        self.log(f"   ✅ Created {clo_count} CLOs across demo courses")

        # 6. Create Users
        self.log("👥 Creating demo faculty/staff...")
        from src.utils.constants import GENERIC_PASSWORD

        default_hash = hash_password(GENERIC_PASSWORD)

        user_ids = self.create_users_from_manifest(
            inst_ids, manifest["users"], program_map, default_hash
        )

        # 7. Create Offerings
        self.log("📋 Creating demo offerings and sections...")

        # Use generic method which handles instructor verification
        # Filter out None values for instructor assignment
        valid_instructor_ids = [uid for uid in user_ids if uid is not None]
        result = self.create_offerings_from_manifest(
            institution_id=inst_ids[0],
            term_id_or_map=term_map,
            offerings_data=manifest["offerings"],
            course_map=course_map,
            instructor_ids=valid_instructor_ids,
        )
        self.log(
            f"   ✅ Created {len(result['offering_ids'])} offerings and {result['section_count']} sections"
        )

        # Apply post-seeding enrichments (CLO overrides + PLOs)
        self._apply_demo_enrichments(manifest, inst_ids[0], term_map, program_map)

        self.log("✅ Demo seeding completed!")
        self.print_summary()
        return True

    def _apply_demo_enrichments(
        self,
        manifest: Dict[str, Any],
        institution_id: str,
        term_map: Dict[str, str],
        program_map: Dict[str, str],
    ) -> None:
        """Apply post-seeding enrichments: section CLO overrides and PLOs."""
        if "section_outcome_overrides" in manifest:
            self.log("🔧 Applying section-specific CLO overrides...")
            override_count = self.apply_section_outcome_overrides(
                manifest["section_outcome_overrides"], institution_id, term_map
            )
            self.log(f"   ✅ Applied {override_count} section outcome overrides")

        if manifest.get("section_narrative_overrides"):
            self.log("📝 Applying instructor narrative overrides...")
            narr_count = self._apply_section_narrative_overrides(
                manifest["section_narrative_overrides"], institution_id, term_map
            )
            self.log(f"   ✅ Applied {narr_count} section narrative overrides")

        if manifest.get("section_feedback_overrides"):
            self.log("💬 Applying reviewer feedback overrides...")
            fb_count = self._apply_section_feedback_overrides(
                manifest["section_feedback_overrides"], institution_id, term_map
            )
            self.log(f"   ✅ Applied {fb_count} section feedback overrides")

        if manifest.get("section_outcome_overrides"):
            self.log("🧠 Backfilling demo narratives + reviewer feedback...")
            backfill_stats = self._backfill_demo_story_data(
                manifest, institution_id, term_map
            )
            self.log(
                "   ✅ Backfilled "
                f"{backfill_stats['narratives']} section narrative set(s) and "
                f"{backfill_stats['feedback']} reviewer feedback item(s)"
            )

        if manifest.get("program_outcomes"):
            self.log("🗺️  Creating Program Learning Outcomes + mappings...")
            plo_stats = self._create_plos_from_manifest(
                manifest["program_outcomes"], program_map, institution_id
            )
            self.log(
                f"   ✅ Created {plo_stats['plo_count']} PLOs, "
                f"mapped {plo_stats['entry_count']} CLOs, "
                f"published {plo_stats['published_count']} mapping version(s)"
            )

    def apply_section_outcome_overrides(
        self,
        overrides: List[Dict[str, Any]],
        institution_id: str,
        term_map: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Apply section-specific CLO status overrides after seeding.

        This allows individual section outcomes to have different statuses
        than the course-level template (e.g., one section submitted, another forgot).

        Args:
            overrides: List of override dicts with course_code, section_number,
                      clo_number, and the updates to apply.  Optional term_code
                      disambiguates when the same course/section exists in
                      multiple terms.
            institution_id: Institution ID to look up course/section
            term_map: Optional mapping of term_code → term_id for
                      term-specific override resolution

        Returns:
            Number of overrides successfully applied
        """
        from src.utils.constants import CLOStatus

        applied_count = 0
        status_lookup = self._status_lookup()

        for override in overrides:
            # Skip JSON comment-only entries
            if "_comment" in override and len(override) == 1:
                continue
            course_code = override.get("course_code")
            section_number = override.get("section_number")
            clo_number = str(override.get("clo_number"))
            new_status = override.get("status", "assigned")

            # Resolve optional term_code → term_id for disambiguation
            term_id = None
            term_code = override.get("term_code")
            if term_code:
                if not term_map:
                    self.log(
                        f"   ⚠️ term_code '{term_code}' provided but no term_map available; "
                        f"skipping override for {course_code} Sec {section_number} CLO {clo_number}"
                    )
                    continue
                term_id = term_map.get(term_code)
                if term_id is None:
                    self.log(
                        f"   ⚠️ Unknown term_code '{term_code}'; "
                        f"skipping override for {course_code} Sec {section_number} CLO {clo_number}"
                    )
                    continue

            # Skip if required fields are missing
            if not course_code or not section_number:
                continue

            # Look up the section outcome to update
            section_outcome = self._find_section_outcome(
                course_code, section_number, clo_number, institution_id, term_id
            )
            if not section_outcome:
                self.log(
                    f"   ⚠️ Section outcome not found: {course_code} Sec {section_number} CLO {clo_number}"
                )
                continue

            # Build updates
            status_enum, approval_status = status_lookup.get(
                new_status, (CLOStatus.ASSIGNED, None)
            )
            updates: Dict[str, Any] = {
                "status": status_enum,
            }
            if approval_status:
                updates["approval_status"] = approval_status

            # Add optional fields
            if "feedback_comments" in override:
                updates["feedback_comments"] = override["feedback_comments"]
            if "students_took" in override:
                updates["students_took"] = override["students_took"]
            if "students_passed" in override:
                updates["students_passed"] = override["students_passed"]

            # Apply the update (this creates history for the current status too,
            # but we'll add explicit historical entries below)
            if database_service.db.update_section_outcome(
                section_outcome["id"], updates
            ):
                applied_count += 1
                self.log(
                    f"   ✓ Updated {course_code} Sec {section_number} CLO {clo_number} → {new_status}"
                )

                # Add explicit history entries from manifest
                if "history" in override:
                    self._create_history_entries(
                        section_outcome["id"], override["history"]
                    )

        return applied_count

    def _apply_section_narrative_overrides(
        self,
        overrides: List[Dict[str, Any]],
        institution_id: str,
        term_map: Optional[Dict[str, str]] = None,
    ) -> int:
        """Update CourseSection records with instructor narrative text.

        Each override specifies a course_code + section_number + term_code and
        one or more narrative fields to set on the section row.
        """
        narrative_fields = {
            "narrative_celebrations",
            "narrative_challenges",
            "narrative_changes",
            "reconciliation_note",
            "students_passed",
            "students_dfic",
        }
        applied = 0
        for entry in overrides:
            if "_comment" in entry and len(entry) <= 2:
                continue
            course_code = entry.get("course_code")
            section_number = entry.get("section_number")
            term_code = entry.get("term_code")
            if not course_code or not section_number:
                continue

            term_id = (term_map or {}).get(term_code) if term_code else None
            section_id = self._resolve_section_id(
                course_code, section_number, institution_id, term_id
            )
            if not section_id:
                self.log(
                    f"   ⚠️ Section not found: {course_code} Sec {section_number}"
                    + (f" term={term_code}" if term_code else "")
                )
                continue

            updates = {k: v for k, v in entry.items() if k in narrative_fields}
            if not updates:
                continue
            if database_service.db.update_course_section(section_id, updates):
                applied += 1
        return applied

    def _apply_section_feedback_overrides(
        self,
        overrides: List[Dict[str, Any]],
        institution_id: str,
        term_map: Optional[Dict[str, str]] = None,
    ) -> int:
        """Set feedback_comments on specific CourseSectionOutcome records."""
        applied = 0
        for entry in overrides:
            if "_comment" in entry and len(entry) <= 2:
                continue
            course_code = entry.get("course_code")
            section_number = entry.get("section_number")
            clo_number_raw = entry.get("clo_number")
            clo_number = str(clo_number_raw) if clo_number_raw is not None else None
            feedback = entry.get("feedback_comments")
            if not course_code or not section_number or not clo_number or not feedback:
                continue

            term_code = entry.get("term_code")
            term_id = (term_map or {}).get(term_code) if term_code else None

            section_outcome = self._find_section_outcome(
                course_code, section_number, clo_number, institution_id, term_id
            )
            if not section_outcome:
                self.log(
                    f"   ⚠️ Section outcome not found: {course_code} "
                    f"Sec {section_number} CLO {clo_number}"
                )
                continue

            if database_service.db.update_section_outcome(
                section_outcome["id"], {"feedback_comments": feedback}
            ):
                applied += 1
        return applied

    @staticmethod
    def _demo_story_profile(course_code: str) -> Dict[str, str]:
        return DEMO_STORY_PROFILES.get(course_code, DEMO_STORY_PROFILES["_default"])

    @staticmethod
    def _demo_term_context(term_code: Optional[str]) -> str:
        return DEMO_TERM_CONTEXT.get(term_code or "", DEMO_TERM_CONTEXT[""])

    def _build_demo_narrative_payload(
        self, course_code: str, term_code: Optional[str], section_number: str
    ) -> Dict[str, Any]:
        profile = self._demo_story_profile(course_code)
        context = self._demo_term_context(term_code)
        section_ref = f"Section {section_number} in {course_code}"
        return {
            "narrative_celebrations": (
                f"{context}{profile['celebration']}. {section_ref} gave us a stable, repeatable demo example rather than a one-off success story."
            ),
            "narrative_challenges": (
                f"{context}{profile['challenge']}. The pattern is consistent enough that it should show up clearly in the drill-through panel."
            ),
            "narrative_changes": (
                f"{context}{profile['change']}. That gives the seeded data a visible 'what we will do next' thread instead of stopping at diagnosis."
            ),
        }

    def _build_demo_feedback_comment(
        self,
        course_code: str,
        term_code: Optional[str],
        clo_number: str,
        students_passed: Optional[int],
        students_took: Optional[int],
    ) -> str:
        profile = self._demo_story_profile(course_code)
        context = self._demo_term_context(term_code).strip()
        rate_text = "limited evidence"
        if students_took:
            rate = round((float(students_passed or 0) / float(students_took)) * 100)
            rate_text = f"{rate}% pass rate"
        return (
            f"{context} {course_code} CLO {clo_number} is sitting at {rate_text} in the seeded data. "
            f"{profile['feedback']}"
        )

    def _backfill_demo_story_data(
        self,
        manifest: Dict[str, Any],
        institution_id: str,
        term_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, int]:
        narrative_overrides = manifest.get("section_narrative_overrides") or []
        feedback_overrides = manifest.get("section_feedback_overrides") or []
        outcome_overrides = manifest.get("section_outcome_overrides") or []

        def _coerce_clo_number(value: Any) -> Optional[str]:
            return str(value) if value is not None else None

        explicit_narratives = {
            (
                entry.get("course_code"),
                entry.get("section_number"),
                entry.get("term_code"),
            )
            for entry in narrative_overrides
            if not ("_comment" in entry and len(entry) <= 2)
        }
        explicit_feedback = {
            (
                entry.get("course_code"),
                entry.get("section_number"),
                _coerce_clo_number(entry.get("clo_number")),
                entry.get("term_code"),
            )
            for entry in feedback_overrides
            if not ("_comment" in entry and len(entry) <= 2)
            if entry.get("clo_number") is not None
        }

        narrative_count = 0
        feedback_count = 0
        seen_sections: set[tuple[str, str, Optional[str]]] = set()

        for entry in outcome_overrides:
            if "_comment" in entry and len(entry) <= 2:
                continue
            course_code = entry.get("course_code")
            section_number = entry.get("section_number")
            term_code = entry.get("term_code")
            clo_number = _coerce_clo_number(entry.get("clo_number"))
            students_took = entry.get("students_took")
            students_passed = entry.get("students_passed")

            if not course_code or not section_number or not clo_number:
                continue
            if not students_took:
                continue

            section_key = (course_code, section_number, term_code)
            feedback_key = (course_code, section_number, clo_number, term_code)
            term_id = (term_map or {}).get(term_code) if term_code else None

            if (
                section_key not in explicit_narratives
                and section_key not in seen_sections
            ):
                section_id = self._resolve_section_id(
                    course_code, section_number, institution_id, term_id
                )
                if section_id:
                    updates = self._build_demo_narrative_payload(
                        course_code, term_code, section_number
                    )
                    if database_service.db.update_course_section(section_id, updates):
                        narrative_count += 1
                        seen_sections.add(section_key)

            if feedback_key in explicit_feedback:
                continue

            section_outcome = self._find_section_outcome(
                course_code, section_number, clo_number, institution_id, term_id
            )
            if not section_outcome:
                continue

            feedback = self._build_demo_feedback_comment(
                course_code,
                term_code,
                clo_number,
                students_passed,
                students_took,
            )
            if database_service.db.update_section_outcome(
                section_outcome["id"], {"feedback_comments": feedback}
            ):
                feedback_count += 1

        return {"narratives": narrative_count, "feedback": feedback_count}

    def _resolve_section_id(
        self,
        course_code: str,
        section_number: str,
        institution_id: str,
        term_id: Optional[str] = None,
    ) -> Optional[str]:
        """Find a section ID by course code and section number."""
        course = database_service.db.get_course_by_number(course_code, institution_id)
        if not course:
            return None
        course_id = course.get("id") or course.get("course_id")
        if not course_id:
            return None
        return self._find_section_id(course_id, section_number, term_id)

    def _create_plos_from_manifest(
        self,
        plo_config: Dict[str, Any],
        program_map: Dict[str, str],
        institution_id: str,
    ) -> Dict[str, int]:
        """Create Program Learning Outcomes and publish PLO↔CLO mappings.

        Manifest shape (per program code)::

            "<PROG_CODE>": {
                "assessment_display_mode": "both" | "percentage" | "binary",
                "plos": [
                    {
                        "plo_number": "PLO-1",
                        "description": "...",
                        "clo_mappings": [
                            {"course_code": "BIOL-101", "clo_number": 1}, ...
                        ]
                    }
                ]
            }

        For each program:
          1. Creates all PLO templates
          2. Opens (or reuses) a draft mapping
          3. Resolves each CLO reference (course_code + clo_number) → CLO id
             and adds a mapping entry
          4. Publishes the draft so the PLO dashboard shows rolled-up
             assessment data immediately after seeding
          5. Writes assessment_display_mode into the program's extras

        Returns counts for the summary log line.
        """
        plo_count = 0
        entry_count = 0
        published_count = 0

        # Cache CLO lookup by (course_code, clo_number) → outcome_id so we
        # only hit the DB once per course.
        clo_cache: Dict[tuple[str, str], Optional[str]] = {}

        def _lookup_clo(course_code: str, clo_num: str) -> Optional[str]:
            key = (course_code, str(clo_num))
            if key in clo_cache:
                return clo_cache[key]
            course = database_service.db.get_course_by_number(
                course_code, institution_id
            )
            if not course:
                clo_cache[key] = None
                return None
            cid = course.get("id") or course.get("course_id")
            if not cid:
                clo_cache[key] = None
                return None
            for co in database_service.db.get_course_outcomes(cid) or []:
                clo_cache[(course_code, str(co.get("clo_number")))] = co.get(
                    "outcome_id"
                ) or co.get("id")
            return clo_cache.get(key)

        for prog_code, config in plo_config.items():
            if prog_code.startswith("_"):  # skip _comment etc.
                continue
            program_id = program_map.get(prog_code)
            if not program_id:
                self.log(
                    f"   ⚠️  Program code '{prog_code}' not in program_map, skipping PLOs"
                )
                continue

            # Persist per-program display preference (lands in Program.extras)
            display_mode = config.get("assessment_display_mode")
            if display_mode:
                database_service.db.update_program(
                    program_id, {"assessment_display_mode": display_mode}
                )

            plo_defs = config.get("plos") or []
            if not plo_defs:
                continue

            # 1. Create PLO templates and remember their IDs
            plo_ids: Dict[str, str] = {}
            for plo_def in plo_defs:
                plo_id = database_service.db.create_program_outcome(
                    {
                        "program_id": program_id,
                        "institution_id": institution_id,
                        "plo_number": plo_def["plo_number"],
                        "description": plo_def.get("description", ""),
                    }
                )
                plo_ids[plo_def["plo_number"]] = plo_id
                plo_count += 1
                self.log(f"   ✓ PLO {plo_def['plo_number']} for {prog_code}")

            # 2. Build mapping entries — only open a draft if there's at
            #    least one CLO link to add (keeps the ZOOL empty-PLO case
            #    from creating an empty published version).
            all_mappings = [
                (plo_def, m)
                for plo_def in plo_defs
                for m in plo_def.get("clo_mappings") or []
            ]
            if not all_mappings:
                continue

            draft = database_service.db.get_or_create_plo_mapping_draft(program_id)
            mapping_id_raw = draft.get("id") or draft.get("mapping_id")
            if not mapping_id_raw:
                self.log(f"   ⚠️  Draft mapping for {prog_code} has no id, skipping")
                continue
            mapping_id: str = str(mapping_id_raw)

            for plo_def, mapping_ref in all_mappings:
                target_plo = plo_ids.get(plo_def["plo_number"])
                target_clo = _lookup_clo(
                    mapping_ref["course_code"], mapping_ref["clo_number"]
                )
                if not target_plo or not target_clo:
                    self.log(
                        "   ⚠️  Could not resolve mapping "
                        f"{plo_def['plo_number']} → "
                        f"{mapping_ref['course_code']} "
                        f"CLO{mapping_ref['clo_number']}"
                    )
                    continue
                database_service.db.add_plo_mapping_entry(
                    mapping_id, target_plo, target_clo
                )
                entry_count += 1

            # 3. Publish the draft so the dashboard has a version of record
            database_service.db.publish_plo_mapping(
                mapping_id, description="Seeded initial PLO→CLO mapping"
            )
            published_count += 1
            self.log(
                f"   ✓ Published PLO mapping v1 for {prog_code} "
                f"({entry_count} total entries so far)"
            )

        return {
            "plo_count": plo_count,
            "entry_count": entry_count,
            "published_count": published_count,
        }

    def _create_history_entries(
        self, section_outcome_id: str, history_data: List[Dict[str, Any]]
    ) -> None:
        """Create OutcomeHistory entries with relative dates from manifest."""
        from datetime import timedelta

        from src.models.models_sql import OutcomeHistory

        now = datetime.now(timezone.utc)

        # Cast to access internal session_scope (demo seeder only)
        db = database_service.db  # type: ignore[assignment,attr-defined]
        with db.sql.session_scope() as session:  # type: ignore[attr-defined]
            for entry in history_data:
                event = entry.get("event")
                relative_days = entry.get("relative_days", 0)
                occurred_at = now + timedelta(days=relative_days)

                history_entry = OutcomeHistory(
                    section_outcome_id=section_outcome_id,
                    event=event,
                    occurred_at=occurred_at,
                )
                session.add(history_entry)

    def _find_section_outcome(
        self,
        course_code: str,
        section_number: str,
        clo_number: str,
        institution_id: str,
        term_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find a specific section outcome by course/section/CLO number."""
        # Step 1: Find the course by course_code
        course = database_service.db.get_course_by_number(course_code, institution_id)
        if not course:
            return None
        course_id = course.get("id") or course.get("course_id")
        if not course_id:
            return None

        # Step 2: Find the course outcome (template) by clo_number
        outcome_id = self._find_outcome_id(course_id, clo_number)
        if not outcome_id:
            return None

        # Step 3: Find the section by section_number (optionally filtered by term)
        section_id = self._find_section_id(course_id, section_number, term_id)
        if not section_id:
            return None

        # Step 4: Find the section outcome by section_id and outcome_id
        section_outcome = (
            database_service.db.get_section_outcome_by_course_outcome_and_section(
                outcome_id, section_id
            )
        )
        return section_outcome

    def _find_outcome_id(self, course_id: str, clo_number: str) -> Optional[str]:
        """Find the outcome template id by CLO number."""
        course_outcomes = database_service.db.get_course_outcomes(course_id)
        for co in course_outcomes or []:
            if str(co.get("clo_number")) == clo_number:
                return co.get("id") or co.get("outcome_id")
        return None

    def _find_section_id(
        self,
        course_id: str,
        section_number: str,
        term_id: Optional[str] = None,
    ) -> Optional[str]:
        """Find section id by section number, optionally filtering by term.

        Caches offering lookups to avoid N+1 queries.
        """
        sections = database_service.db.get_sections_by_course(course_id)
        offering_term_cache: dict[str, Optional[str]] = {}
        for sec in sections or []:
            if sec.get("section_number") != section_number:
                continue
            if term_id and not self._section_matches_term(
                sec, term_id, offering_term_cache
            ):
                continue
            return sec.get("id") or sec.get("section_id")
        return None

    @staticmethod
    def _section_matches_term(
        sec: Dict[str, Any],
        term_id: str,
        offering_cache: dict[str, Optional[str]],
    ) -> bool:
        """Check if a section belongs to the given term (with caching)."""
        offering_id = sec.get("offering_id")
        if not offering_id:
            return False
        if offering_id not in offering_cache:
            offering = database_service.db.get_course_offering(offering_id)
            offering_cache[offering_id] = offering.get("term_id") if offering else None
        return offering_cache[offering_id] == term_id

    def print_summary(self) -> None:
        """Print demo seeding summary"""
        self.log("")
        self.log("📊 Seeding Complete:")
        self.log(f"   Institutions: {len(self.created['institutions'])} created")
        self.log(f"   Users: {len(self.created['users'])} created")
        self.log(f"   Terms: {len(self.created['terms'])} created")
        self.log(f"   Courses: {len(self.created['courses'])} created")
        self.log("")

        # Environment-specific next steps
        if self.env == "local":
            self.log("🎬 Next Steps (Local Development):")
            self.log("   1. Restart server: ./scripts/restart_server.sh local")
            self.log("   2. Navigate to: http://localhost:3001")
            self.log(self.LOGIN_WITH_DEMO_CREDENTIALS_MSG)
            self.log("")
            self.log("💡 Monitor logs: ./scripts/monitor_logs.sh")
        elif self.env == "dev":
            self.log("🎬 Next Steps (Dev Environment):")
            self.log(self.NEON_SEEDED_MSG)
            self.log("   2. Navigate to: https://dev.loopcloser.io")
            self.log(self.LOGIN_WITH_DEMO_CREDENTIALS_MSG)
            self.log("")
            self.log(
                "💡 Note: Cloud Run app restarts automatically, no manual restart needed"
            )
        elif self.env == "staging":
            self.log("🎬 Next Steps (Staging Environment):")
            self.log(self.NEON_SEEDED_MSG)
            self.log("   2. Navigate to: https://staging.loopcloser.io")
            self.log(self.LOGIN_WITH_DEMO_CREDENTIALS_MSG)
        elif self.env == "prod":
            self.log("🎬 Next Steps (Production Environment):")
            self.log(self.NEON_SEEDED_MSG)
            self.log("   2. Navigate to: https://loopcloser.io")
            self.log(self.LOGIN_WITH_DEMO_CREDENTIALS_MSG)
            self.log("")
            self.log("⚠️  Production database modified - verify data integrity!")
        elif self.env == "e2e":
            self.log("🎬 Next Steps (E2E Testing):")
            self.log("   1. Restart server: ./scripts/restart_server.sh e2e")
            self.log("   2. Run E2E tests: npm run test:e2e")
            self.log("")
            self.log("💡 Monitor logs: ./scripts/monitor_logs.sh")
        elif self.env == "smoke":
            self.log("🎬 Next Steps (Smoke Testing):")
            self.log("   1. Restart server: ./scripts/restart_server.sh smoke")
            self.log("   2. Run smoke tests")
        else:
            self.log("🎬 Next Steps:")
            self.log(f"   Environment: {self.env}")
            self.log("   Check environment-specific documentation")


def _resolve_database_url(args: argparse.Namespace) -> str:
    """Resolve database URL based on environment and configuration."""
    # Environment-specific Neon database URLs (set these in .envrc)
    neon_env_mapping = {
        "dev": os.environ.get("NEON_DB_URL_DEV"),
        "staging": os.environ.get("NEON_DB_URL_STAGING"),
        "prod": os.environ.get("NEON_DB_URL_PROD"),
    }

    # Local SQLite database mapping (for local/test envs only)
    local_db_mapping = {
        "local": "sqlite:///loopcloser_dev.db",
        "e2e": "sqlite:///loopcloser_e2e.db",
        "smoke": "sqlite:///loopcloser_smoke.db",
        "ci": "sqlite:///loopcloser_ci.db",
    }

    deployed_environments = ["dev", "staging", "prod"]

    # Priority: DATABASE_URL → NEON_DB_URL_* → Local SQLite
    existing_db_url = os.environ.get("DATABASE_URL")
    if existing_db_url:
        print(
            f"\n[SEED] 🗄️  Using manual DATABASE_URL override: {existing_db_url[:50]}..."
        )
        return existing_db_url
    elif args.env in neon_env_mapping and neon_env_mapping[args.env]:
        database_url = neon_env_mapping[args.env]
        if not database_url:  # type guard for mypy
            raise ValueError(f"NEON_DB_URL_{args.env.upper()} is not set")
        print(
            f"\n[SEED] 🗄️  Using {args.env.upper()} Neon database: {database_url[:50]}..."
        )
        return database_url
    elif args.env in deployed_environments:
        # Deployed environments REQUIRE Neon URL
        print(
            f"\n❌ ERROR: {args.env.upper()} environment requires NEON_DB_URL_{args.env.upper()} to be set"
        )
        print(f"\nPlease add this to your .envrc file:")
        print(f'  export NEON_DB_URL_{args.env.upper()}="postgresql://..."')
        print(f"\nThen run: direnv allow .\n")
        sys.exit(1)
    else:
        # Local SQLite fallback
        database_url = local_db_mapping.get(args.env, "sqlite:///loopcloser.db")
        print(f"\n[SEED] 🗄️  Using local {args.env} database: {database_url}")
        return database_url


def _confirm_deployed_environment(args: argparse.Namespace, database_url: str) -> None:
    """Require human confirmation for remote database seeding."""
    # AGENTS SHOULD NOT MODIFY THIS FUNCTION TO SKIP HUMAN VERIFICATION
    # DO NOT ADD FLAGS TO BYPASS CONFIRMATION PROMPTS
    deployed_environments = ["dev", "staging", "prod"]

    # Require confirmation if:
    # 1. We are targeting a deployed environment (dev, staging, prod)
    # 2. OR the database URL looks like a remote PostgreSQL database
    if args.env not in deployed_environments and not database_url.startswith(
        "postgresql://"
    ):
        return  # Local env AND local DB - no confirmation needed

    print("\n" + "=" * 70)
    print("⚠️  REMOTE DATABASE SEEDING - CONFIRMATION REQUIRED")
    print("=" * 70)

    # Parse database info
    if database_url.startswith("postgresql://"):
        db_type = "PostgreSQL (Neon)"
        hostname_start = database_url.find("@")
        hostname_end = (
            database_url.find("/", hostname_start) if hostname_start != -1 else -1
        )
        hostname = (
            database_url[hostname_start + 1 : hostname_end]
            if hostname_start != -1 and hostname_end != -1
            else "unknown"
        )
    elif database_url.startswith("sqlite:///"):
        db_type = "SQLite (local file)"
        hostname = database_url.replace("sqlite:///", "")
    else:
        db_type = "Unknown"
        hostname = database_url[:50]

    print(f"\nEnvironment: {args.env.upper()}")
    print(f"Database Type: {db_type}")
    print(f"Target: {hostname}")
    print(f"\n⚠️  You are about to seed a REMOTE database!")

    if args.clear:
        print("\n🚨 DESTRUCTIVE OPERATION: --clear flag will WIPE ALL DATA")

    print("\n" + "-" * 70)
    print("To proceed, type 'yes' (lowercase, exactly)")
    print("To cancel, press Ctrl+C or type anything else")
    print("-" * 70)

    try:
        confirmation = input("\nType 'yes' to confirm: ").strip()
    except KeyboardInterrupt:
        print("\n\n❌ Seeding cancelled by user\n")
        sys.exit(0)

    if confirmation != "yes":
        print(f"\n❌ Confirmation failed. Expected 'yes', got '{confirmation}'")
        print("Seeding cancelled - no changes made\n")
        sys.exit(0)

    print("\n✅ Confirmation received. Proceeding with remote seeding...\n")


def _clear_flask_sessions() -> None:
    """Clear Flask server-side session files to force re-login after DB reset.

    Flask-Session stores sessions as files in ``flask_session/`` (the default
    ``SESSION_FILE_DIR``).  When the database is wiped the user rows disappear
    but stale session files keep browsers "logged in", which is confusing.
    Removing these files ensures every user must authenticate again.
    """
    import glob

    session_dirs = [
        os.path.join(project_root, "flask_session"),
        os.path.join(project_root, "data", "flask_session"),
    ]

    cleared = 0
    for session_dir in session_dirs:
        if os.path.isdir(session_dir):
            files = glob.glob(os.path.join(session_dir, "*"))
            cleared += len(files)
            for f in files:
                try:
                    os.remove(f)
                except OSError:
                    pass
    if cleared:
        print(f"  🗑️  Cleared {cleared} session file(s)")


def _rotate_db_generation() -> None:
    """Write a new database generation token to invalidate stale sessions.

    Any browser session whose stored ``_db_generation`` doesn't match the new
    token will be destroyed on the next request, forcing a clean re-login.
    See ``auth_service._get_session_user()`` for the check.
    """
    from src.services.auth_service import write_db_generation

    token = write_db_generation()
    print(f"  🔑 Rotated database generation token: {token[:8]}…")


def _execute_seeding(args: argparse.Namespace) -> bool:
    """Execute the seeding operation."""
    if args.demo:
        demo_seeder = DemoSeeder(manifest_path=args.manifest, env=args.env)
        if args.clear:
            demo_seeder.log("🧹 Clearing database...")
            from src.database.database_service import reset_database

            reset_database()
            _clear_flask_sessions()
            _rotate_db_generation()
        return demo_seeder.seed_demo()
    else:
        baseline_seeder = BaselineTestSeeder()
        if args.clear:
            baseline_seeder.log("🧹 Clearing database...")
            from src.database.database_service import reset_database

            reset_database()
            _clear_flask_sessions()
            _rotate_db_generation()

        # Load manifest if provided
        manifest_data = None
        if args.manifest:
            try:
                with open(args.manifest, "r") as f:
                    manifest_data = json.load(f)
                baseline_seeder.log(f"📄 Loaded custom manifest: {args.manifest}")
            except Exception as e:
                print(f"❌ Failed to load manifest: {e}")
                sys.exit(1)

        return baseline_seeder.seed_baseline(manifest_data)


def main() -> None:
    """Main seeding entry point"""
    parser = argparse.ArgumentParser(
        description="Seed database with test or demo data",
        epilog="Examples:\n"
        "  python scripts/seed_db.py --demo --clear --env local    # Local SQLite dev database\n"
        "  python scripts/seed_db.py --demo --clear --env dev      # Deployed dev (uses NEON_DB_URL_DEV if set)\n"
        "  python scripts/seed_db.py --clear --env e2e             # E2E test database\n"
        "  python scripts/seed_db.py --env staging                 # Staging environment\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--clear", action="store_true", help="Clear database first")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Seed generic demo environment for product demonstrations",
    )
    parser.add_argument(
        "--env",
        choices=["local", "dev", "e2e", "smoke", "ci", "staging", "prod"],
        required=True,
        help="Environment to seed. 'local' = local SQLite dev database, 'dev' = deployed dev environment (Neon if NEON_DB_URL_DEV set), 'staging' = staging environment, 'prod' = production.",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to JSON manifest file for custom seeding (overrides generic defaults)",
    )

    # Parse arguments and catch errors
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code != 0:
            print("\n❌ ERROR: Invalid arguments provided")
            print("💡 TIP: Use --env local (not just 'local')")
            print("Run with -h or --help for usage information\n")
        raise

    # Resolve database URL
    database_url = _resolve_database_url(args)
    os.environ["DATABASE_URL"] = database_url

    # Require confirmation for deployed environments
    _confirm_deployed_environment(args, database_url)

    # Refresh database connection
    from src.database import database_service

    database_service.refresh_connection()

    # Execute seeding
    success = _execute_seeding(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
