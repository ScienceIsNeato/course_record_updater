"""Workflow and history mixin for the SQLAlchemy-backed database implementation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from src.database.database_sql import SQLService
from src.models.models_sql import (
    PloMapping,
    PloMappingEntry,
    ProgramOutcome,
    User,
    UserInvitation,
    to_dict,
)
from src.utils.logging_config import get_logger
from src.utils.time_utils import get_current_time

MAPPING_NOT_FOUND_MSG = "Mapping {mapping_id} not found"

from .database_sqlite_shared import _ensure_uuid

logger = get_logger(__name__)


class SQLDatabaseWorkflowMixin:
    sql: SQLService

    def create_invitation(self, invitation_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(invitation_data)
        invitation_id = _ensure_uuid(payload.pop("invitation_id", None))

        exclude_fields = {
            "invitation_id",
            "email",
            "role",
            "institution_id",
            "token",
            "invited_by",
            "invited_at",
            "expires_at",
            "status",
            "accepted_at",
            "personal_message",
            "created_at",
            "updated_at",
        }
        extras_dict = {k: v for k, v in payload.items() if k not in exclude_fields}
        extras_dict["invitation_id"] = invitation_id

        invitation = UserInvitation(
            id=invitation_id,
            email=payload.get("email", "").lower(),
            role=payload.get("role", "instructor"),
            institution_id=payload.get("institution_id"),
            token=payload.get("token", str(uuid.uuid4())),
            invited_by=payload.get("invited_by"),
            invited_at=payload.get("invited_at", get_current_time()),
            expires_at=payload.get("expires_at"),
            status=payload.get("status", "pending"),
            accepted_at=payload.get("accepted_at"),
            personal_message=payload.get("personal_message"),
            extras=extras_dict,
        )
        with self.sql.session_scope() as session:
            session.add(invitation)
            session.flush()
            return invitation_id

    def get_invitation_by_id(self, invitation_id: str) -> Optional[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            invitation = session.get(UserInvitation, invitation_id)
            return to_dict(invitation) if invitation else None

    def get_invitation_by_token(
        self, invitation_token: str
    ) -> Optional[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            invitation = (
                session.execute(
                    select(UserInvitation).where(
                        UserInvitation.token == invitation_token
                    )
                )
                .scalars()
                .first()
            )
            return to_dict(invitation) if invitation else None

    def get_invitation_by_email(
        self, email: str, institution_id: str
    ) -> Optional[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            invitation = (
                session.execute(
                    select(UserInvitation)
                    .where(
                        and_(
                            UserInvitation.email == email.lower(),
                            UserInvitation.institution_id == institution_id,
                        )
                    )
                    .order_by(UserInvitation.created_at.desc())
                )
                .scalars()
                .first()
            )
            return to_dict(invitation) if invitation else None

    def update_invitation(self, invitation_id: str, updates: Dict[str, Any]) -> bool:
        with self.sql.session_scope() as session:
            invitation = session.execute(
                select(UserInvitation).where(UserInvitation.id == invitation_id)
            ).scalar_one_or_none()
            if not invitation:
                return False
            for key, value in updates.items():
                if hasattr(UserInvitation, key):
                    setattr(invitation, key, value)
                else:
                    logger.warning(
                        "[SQLDatabase] Unknown attribute '%s' for UserInvitation; storing in extras.",
                        logger.sanitize(key),
                    )
                    invitation.extras[key] = value
            invitation.updated_at = datetime.now(timezone.utc)
            return True

    def list_invitations(
        self, institution_id: str, status: Optional[str], limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            query = select(UserInvitation).where(
                UserInvitation.institution_id == institution_id
            )
            if status:
                query = query.where(UserInvitation.status == status)
            query = query.order_by(UserInvitation.invited_at.desc())
            invitations = (
                session.execute(query.offset(offset).limit(limit)).scalars().all()
            )
            return [to_dict(invitation) for invitation in invitations]

    def create_audit_log(self, audit_data: Dict[str, Any]) -> bool:
        from src.models.models_sql import AuditLog

        try:
            with self.sql.session_scope() as session:
                audit_log = AuditLog(**audit_data)
                session.add(audit_log)
                return True
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            return False

    def get_audit_logs_by_entity(
        self, entity_type: str, entity_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        from src.models.models_sql import AuditLog

        try:
            with self.sql.session_scope() as session:
                query = select(AuditLog).where(
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == entity_id,
                )
                query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
                logs = session.execute(query).scalars().all()
                return [self._audit_log_to_dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get entity audit logs: {e}")
            return []

    def get_audit_logs_by_user(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        from src.models.models_sql import AuditLog

        try:
            with self.sql.session_scope() as session:
                query = select(AuditLog).where(AuditLog.user_id == user_id)

                if start_date:
                    query = query.where(AuditLog.timestamp >= start_date)
                if end_date:
                    query = query.where(AuditLog.timestamp <= end_date)

                query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
                logs = session.execute(query).scalars().all()
                return [self._audit_log_to_dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get user audit logs: {e}")
            return []

    def get_recent_audit_logs(
        self, institution_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        from src.models.models_sql import AuditLog

        try:
            with self.sql.session_scope() as session:
                query = select(AuditLog)

                if institution_id:
                    query = query.where(AuditLog.institution_id == institution_id)

                query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
                logs = session.execute(query).scalars().all()
                return [self._audit_log_to_dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get recent audit logs: {e}")
            return []

    def get_audit_logs_filtered(
        self,
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[str] = None,
        user_id: Optional[str] = None,
        institution_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        from src.models.models_sql import AuditLog

        try:
            with self.sql.session_scope() as session:
                query = select(AuditLog).where(
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date,
                )

                if entity_type:
                    query = query.where(AuditLog.entity_type == entity_type)
                if user_id:
                    query = query.where(AuditLog.user_id == user_id)
                if institution_id:
                    query = query.where(AuditLog.institution_id == institution_id)

                query = query.order_by(AuditLog.timestamp.desc())
                logs = session.execute(query).scalars().all()
                return [self._audit_log_to_dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get filtered audit logs: {e}")
            return []

    def _audit_log_to_dict(self, log: Any) -> Dict[str, Any]:
        return {
            "audit_id": log.audit_id,
            "timestamp": log.timestamp,
            "user_id": log.user_id,
            "user_email": log.user_email,
            "user_role": log.user_role,
            "operation_type": log.operation_type,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "changed_fields": log.changed_fields,
            "source_type": log.source_type,
            "source_details": log.source_details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "request_id": log.request_id,
            "session_id": log.session_id,
            "institution_id": log.institution_id,
        }

    def create_reminder(
        self,
        section_id: str,
        instructor_id: str,
        sent_by: Optional[str] = None,
        reminder_type: str = "individual",
        message_preview: Optional[str] = None,
    ) -> Optional[str]:
        from src.models.models_sql import InstructorReminder

        with self.sql.session_scope() as session:
            reminder = InstructorReminder(
                section_id=section_id,
                instructor_id=instructor_id,
                sent_by=sent_by,
                reminder_type=reminder_type,
                message_preview=message_preview[:100] if message_preview else None,
            )
            session.add(reminder)
            session.flush()
            reminder_id = str(reminder.id)
            logger.info(
                "[SQLDatabase] Created reminder %s for section %s",
                reminder_id,
                section_id,
            )
            return reminder_id

    def get_reminders_by_section(self, section_id: str) -> List[Dict[str, Any]]:
        from src.models.models_sql import InstructorReminder

        with self.sql.session_scope() as session:
            reminders = (
                session.query(InstructorReminder)
                .filter(InstructorReminder.section_id == section_id)
                .order_by(InstructorReminder.sent_at.desc())
                .all()
            )
            return [self._reminder_to_dict(r) for r in reminders]

    def get_reminders_by_instructor(self, instructor_id: str) -> List[Dict[str, Any]]:
        from src.models.models_sql import InstructorReminder

        with self.sql.session_scope() as session:
            reminders = (
                session.query(InstructorReminder)
                .filter(InstructorReminder.instructor_id == instructor_id)
                .order_by(InstructorReminder.sent_at.desc())
                .all()
            )
            return [self._reminder_to_dict(r) for r in reminders]

    def _reminder_to_dict(self, reminder: Any) -> Dict[str, Any]:
        return {
            "id": reminder.id,
            "section_id": reminder.section_id,
            "instructor_id": reminder.instructor_id,
            "sent_at": reminder.sent_at,
            "sent_by": reminder.sent_by,
            "reminder_type": reminder.reminder_type,
            "message_preview": reminder.message_preview,
            "created_at": reminder.created_at,
        }

    def add_outcome_history(self, section_outcome_id: str, event: str) -> bool:
        from src.models.models_sql import OutcomeHistory

        try:
            with self.sql.session_scope() as session:
                entry = OutcomeHistory(
                    section_outcome_id=section_outcome_id,
                    event=event,
                    occurred_at=datetime.now(timezone.utc),
                )
                session.add(entry)
                logger.info(
                    "[SQLDatabase] Added history: %s for %s",
                    event,
                    section_outcome_id,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to add outcome history: {e}")
            return False

    def get_outcome_history(self, section_outcome_id: str) -> List[Dict[str, Any]]:
        from src.models.models_sql import OutcomeHistory

        with self.sql.session_scope() as session:
            entries = (
                session.query(OutcomeHistory)
                .filter(OutcomeHistory.section_outcome_id == section_outcome_id)
                .order_by(OutcomeHistory.occurred_at.desc())
                .all()
            )
            return [{"event": e.event, "occurred_at": e.occurred_at} for e in entries]

    def create_program_outcome(self, outcome_data: Dict[str, Any]) -> str:
        payload = dict(outcome_data)
        outcome_id = _ensure_uuid(payload.pop("id", None))

        exclude_fields = {
            "id",
            "program_id",
            "institution_id",
            "plo_number",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        }
        extras_dict = {k: v for k, v in payload.items() if k not in exclude_fields}

        outcome = ProgramOutcome(
            id=outcome_id,
            program_id=payload["program_id"],
            institution_id=payload["institution_id"],
            plo_number=payload["plo_number"],
            description=payload.get("description", ""),
            is_active=payload.get("is_active", True),
            extras=extras_dict if extras_dict else {},
        )

        with self.sql.session_scope() as session:
            session.add(outcome)
            return outcome_id

    def update_program_outcome(
        self, outcome_id: str, outcome_data: Dict[str, Any]
    ) -> bool:
        try:
            with self.sql.session_scope() as session:
                outcome = session.get(ProgramOutcome, outcome_id)
                if not outcome:
                    return False

                for key, value in outcome_data.items():
                    if hasattr(outcome, key) and key != "id":
                        setattr(outcome, key, value)

                return True
        except Exception as e:
            logger.error(f"Failed to update program outcome: {e}")
            return False

    def delete_program_outcome(self, outcome_id: str) -> bool:
        try:
            with self.sql.session_scope() as session:
                outcome = session.get(ProgramOutcome, outcome_id)
                if not outcome:
                    return False

                outcome.is_active = False
                return True
        except Exception as e:
            logger.error(f"Failed to soft-delete program outcome: {e}")
            return False

    def get_program_outcomes(
        self, program_id: str, include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            stmt = select(ProgramOutcome).where(ProgramOutcome.program_id == program_id)
            if not include_inactive:
                stmt = stmt.where(ProgramOutcome.is_active.is_(True))
            stmt = stmt.order_by(ProgramOutcome.plo_number)

            outcomes = session.execute(stmt).scalars().all()
            return [to_dict(o) for o in outcomes]

    def get_program_outcome(self, outcome_id: str) -> Optional[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            outcome = session.get(ProgramOutcome, outcome_id)
            return to_dict(outcome) if outcome else None

    def get_or_create_plo_mapping_draft(
        self, program_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        with self.sql.session_scope() as session:
            draft = (
                session.execute(
                    select(PloMapping).where(
                        and_(
                            PloMapping.program_id == program_id,
                            PloMapping.status == "draft",
                        )
                    )
                )
                .scalars()
                .first()
            )
            if draft:
                _ = draft.entries
                return to_dict(draft)

            draft_id = str(uuid.uuid4())
            draft = PloMapping(
                id=draft_id,
                program_id=program_id,
                status="draft",
                created_by_user_id=user_id,
            )
            session.add(draft)
            session.flush()

            latest = (
                session.execute(
                    select(PloMapping)
                    .where(
                        and_(
                            PloMapping.program_id == program_id,
                            PloMapping.status == "published",
                        )
                    )
                    .order_by(PloMapping.version.desc())
                )
                .scalars()
                .first()
            )
            if latest:
                for entry in latest.entries:
                    new_entry = PloMappingEntry(
                        id=str(uuid.uuid4()),
                        mapping_id=draft_id,
                        program_outcome_id=entry.program_outcome_id,
                        course_outcome_id=entry.course_outcome_id,
                    )
                    session.add(new_entry)

            session.flush()
            _ = draft.entries
            return to_dict(draft)

    def get_plo_mapping_draft(self, program_id: str) -> Optional[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            draft = (
                session.execute(
                    select(PloMapping)
                    .where(
                        and_(
                            PloMapping.program_id == program_id,
                            PloMapping.status == "draft",
                        )
                    )
                    .options(selectinload(PloMapping.entries))
                )
                .scalars()
                .first()
            )
            return to_dict(draft) if draft else None

    def add_plo_mapping_entry(
        self,
        mapping_id: str,
        program_outcome_id: str,
        course_outcome_id: str,
    ) -> str:
        entry_id = str(uuid.uuid4())
        with self.sql.session_scope() as session:
            mapping = session.get(PloMapping, mapping_id)
            if not mapping:
                raise ValueError(MAPPING_NOT_FOUND_MSG.format(mapping_id=mapping_id))
            if mapping.status != "draft":
                raise ValueError("Cannot add entries to a published mapping")
            entry = PloMappingEntry(
                id=entry_id,
                mapping_id=mapping_id,
                program_outcome_id=program_outcome_id,
                course_outcome_id=course_outcome_id,
            )
            session.add(entry)
        return entry_id

    def remove_plo_mapping_entry(self, entry_id: str) -> bool:
        try:
            with self.sql.session_scope() as session:
                entry = session.get(PloMappingEntry, entry_id)
                if not entry:
                    return False

                mapping = session.get(PloMapping, entry.mapping_id)
                if not mapping or mapping.status != "draft":
                    logger.warning(
                        "Refused to remove entry %s: parent mapping %s is not a draft (status=%s)",
                        entry_id,
                        entry.mapping_id,
                        getattr(mapping, "status", None),
                    )
                    return False

                session.delete(entry)
                return True
        except Exception as e:
            logger.error(f"Failed to remove mapping entry: {e}")
            return False

    def publish_plo_mapping(
        self,
        mapping_id: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self.sql.session_scope() as session:
            draft = session.get(PloMapping, mapping_id)
            if not draft or draft.status != "draft":
                raise ValueError(
                    f"Mapping {mapping_id} is not a draft or does not exist"
                )

            max_version = (
                session.execute(
                    select(func.max(PloMapping.version)).where(
                        and_(
                            PloMapping.program_id == draft.program_id,
                            PloMapping.status == "published",
                        )
                    )
                ).scalar()
            ) or 0
            next_version = max_version + 1

            for entry in draft.entries:
                plo = session.get(ProgramOutcome, entry.program_outcome_id)
                if plo:
                    entry.plo_description_snapshot = plo.description

            draft.version = next_version
            draft.status = "published"
            draft.description = description
            draft.published_at = datetime.now(timezone.utc)

            session.flush()
            _ = draft.entries
            return to_dict(draft)

    def discard_plo_mapping_draft(self, mapping_id: str) -> bool:
        try:
            with self.sql.session_scope() as session:
                draft = session.get(PloMapping, mapping_id)
                if not draft or draft.status != "draft":
                    return False
                session.delete(draft)
                return True
        except Exception as e:
            logger.error(f"Failed to discard draft mapping: {e}")
            return False

    def get_plo_mapping(self, mapping_id: str) -> Optional[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            mapping = (
                session.execute(
                    select(PloMapping)
                    .where(PloMapping.id == mapping_id)
                    .options(selectinload(PloMapping.entries))
                )
                .scalars()
                .first()
            )
            return to_dict(mapping) if mapping else None

    def get_plo_mapping_by_version(
        self, program_id: str, version: int
    ) -> Optional[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            mapping = (
                session.execute(
                    select(PloMapping)
                    .where(
                        and_(
                            PloMapping.program_id == program_id,
                            PloMapping.version == version,
                            PloMapping.status == "published",
                        )
                    )
                    .options(selectinload(PloMapping.entries))
                )
                .scalars()
                .first()
            )
            return to_dict(mapping) if mapping else None

    def get_published_plo_mappings(self, program_id: str) -> List[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            mappings = (
                session.execute(
                    select(PloMapping)
                    .where(
                        and_(
                            PloMapping.program_id == program_id,
                            PloMapping.status == "published",
                        )
                    )
                    .order_by(PloMapping.version)
                    .options(selectinload(PloMapping.entries))
                )
                .scalars()
                .all()
            )
            return [to_dict(m) for m in mappings]

    def get_latest_published_plo_mapping(
        self, program_id: str
    ) -> Optional[Dict[str, Any]]:
        with self.sql.session_scope() as session:
            mapping = (
                session.execute(
                    select(PloMapping)
                    .where(
                        and_(
                            PloMapping.program_id == program_id,
                            PloMapping.status == "published",
                        )
                    )
                    .order_by(PloMapping.version.desc())
                    .options(selectinload(PloMapping.entries))
                )
                .scalars()
                .first()
            )
            return to_dict(mapping) if mapping else None

    def delete_user(self, user_id: str) -> bool:
        with self.sql.session_scope() as session:
            user = session.get(User, user_id)
            if not user:
                return False
            session.delete(user)
            return True
