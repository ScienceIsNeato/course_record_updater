"""Abstract database interface for Course Record Updater."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class DatabaseInterface(ABC):
    """Database abstraction contract."""

    # Institution operations
    @abstractmethod
    def create_institution(self, institution_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def get_institution_by_id(self, institution_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_all_institutions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_default_cei_institution(self) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def create_new_institution(
        self, institution_data: Dict[str, Any], admin_user_data: Dict[str, Any]
    ) -> Optional[Tuple[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def get_institution_instructor_count(self, institution_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_institution_by_short_name(
        self, short_name: str
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    # User operations
    @abstractmethod
    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_user_by_reset_token(self, reset_token: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_all_users(self, institution_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def update_user_active_status(self, user_id: str, active_user: bool) -> bool:
        raise NotImplementedError

    @abstractmethod
    def calculate_and_update_active_users(self, institution_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def update_user_extended(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_user_by_verification_token(self, token: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    # Course operations
    @abstractmethod
    def create_course(self, course_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def get_course_by_number(self, course_number: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_courses_by_department(
        self, institution_id: str, department: str
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_course_outcome(self, outcome_data: Dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_course_outcomes(self, course_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_course_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_all_courses(self, institution_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_all_instructors(self, institution_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_all_sections(self, institution_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_course_offering(self, offering_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def get_course_offering(self, offering_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_course_offering_by_course_and_term(
        self, course_id: str, term_id: str
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_all_course_offerings(self, institution_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    # Term operations
    @abstractmethod
    def create_term(self, term_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def get_term_by_name(
        self, name: str, institution_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_active_terms(self, institution_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_sections_by_term(self, term_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    # Section operations
    @abstractmethod
    def create_course_section(self, section_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def get_sections_by_instructor(self, instructor_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    # Program operations
    @abstractmethod
    def create_program(self, program_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def get_programs_by_institution(self, institution_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_program_by_id(self, program_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_program_by_name_and_institution(
        self, program_name: str, institution_id: str
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def update_program(self, program_id: str, updates: Dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_program(self, program_id: str, reassign_to_program_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_courses_by_program(self, program_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_unassigned_courses(self, institution_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def assign_course_to_default_program(
        self, course_id: str, institution_id: str
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def add_course_to_program(self, course_id: str, program_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def remove_course_from_program(self, course_id: str, program_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def bulk_add_courses_to_program(
        self, course_ids: List[str], program_id: str
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def bulk_remove_courses_from_program(
        self, course_ids: List[str], program_id: str
    ) -> Dict[str, Any]:
        raise NotImplementedError

    # Invitation operations
    @abstractmethod
    def create_invitation(self, invitation_data: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def get_invitation_by_id(self, invitation_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_invitation_by_token(
        self, invitation_token: str
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_invitation_by_email(
        self, email: str, institution_id: str
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def update_invitation(self, invitation_id: str, updates: Dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_invitations(
        self, institution_id: str, status: Optional[str], limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError
