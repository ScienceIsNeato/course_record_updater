"""
Audit Logging Service for Course Record Updater

Provides comprehensive audit logging for all CRUD operations with:
- Full change tracking (before/after states)
- User attribution and role tracking
- Multi-tenant context support
- Compliance-ready export capabilities
- Entity history and user activity queries
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.database.database_service import _db_service as db
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class OperationType(Enum):
    """Types of auditable operations"""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class EntityType(Enum):
    """Types of entities we audit"""

    USER = "users"
    INSTITUTION = "institutions"
    PROGRAM = "programs"
    COURSE = "courses"
    TERM = "terms"
    OFFERING = "course_offerings"
    SECTION = "course_sections"
    OUTCOME = "course_outcomes"
    INVITATION = "user_invitations"


class SourceType(Enum):
    """Where the operation originated"""

    API = "API"  # From API request
    IMPORT = "IMPORT"  # From data import
    SYSTEM = "SYSTEM"  # Automated system action
    SCRIPT = "SCRIPT"  # From management script


# Sensitive fields that should be redacted in audit logs
SENSITIVE_FIELDS = [
    "password",
    "password_hash",
    "password_reset_token",
    "email_verification_token",
    "oauth_id",
    "oauth_token",
    "oauth_secret",
    "api_key",
    "secret_key",
    "private_key",
]


def sanitize_for_audit(entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive fields before audit logging

    Args:
        entity_data: Entity data dictionary

    Returns:
        Sanitized dictionary with sensitive fields redacted
    """
    if not entity_data:
        return {}

    sanitized = entity_data.copy()

    for field in SENSITIVE_FIELDS:
        if field in sanitized:
            sanitized[field] = "[REDACTED]"

    return sanitized


def get_changed_fields(
    old_values: Dict[str, Any], new_values: Dict[str, Any]
) -> List[str]:
    """
    Determine which fields changed between old and new values

    Args:
        old_values: Original entity state
        new_values: Updated entity state

    Returns:
        List of field names that changed
    """
    if not old_values or not new_values:
        return []

    changed = []
    all_keys = set(old_values.keys()) | set(new_values.keys())

    for key in all_keys:
        old_val = old_values.get(key)
        new_val = new_values.get(key)

        # Handle datetime comparison
        if isinstance(old_val, datetime) and isinstance(new_val, datetime):
            if old_val.replace(microsecond=0) != new_val.replace(microsecond=0):
                changed.append(key)
        elif old_val != new_val:
            changed.append(key)

    return changed


class AuditService:
    """Service for creating and querying audit logs"""

    @staticmethod
    def log_create(
        entity_type: EntityType,
        entity_id: str,
        new_values: Dict[str, Any],
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        institution_id: Optional[str] = None,
        source_type: SourceType = SourceType.API,
        source_details: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Log entity creation

        Args:
            entity_type: Type of entity created
            entity_id: ID of created entity
            new_values: Complete entity state after creation
            user_id: User who created (NULL for system)
            user_email: User email for quick reference
            user_role: User role at time of action
            institution_id: Institution context
            source_type: Where operation originated
            source_details: Additional context
            request_context: Request metadata (IP, user agent, etc.)

        Returns:
            audit_id: ID of created audit log entry
        """
        try:
            audit_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc)

            # Sanitize sensitive data
            sanitized_new = sanitize_for_audit(new_values)

            # Extract request context
            ip_address = None
            user_agent = None
            request_id = None
            session_id = None

            if request_context:
                ip_address = request_context.get("ip_address")
                user_agent = request_context.get("user_agent")
                request_id = request_context.get("request_id")
                session_id = request_context.get("session_id")

            audit_entry = {
                "audit_id": audit_id,
                "timestamp": timestamp,
                # Who
                "user_id": user_id,
                "user_email": user_email,
                "user_role": user_role,
                # What
                "operation_type": OperationType.CREATE.value,
                "entity_type": entity_type.value,
                "entity_id": entity_id,
                # Changes
                "old_values": None,  # NULL for CREATE
                "new_values": json.dumps(sanitized_new),
                "changed_fields": None,  # Not applicable for CREATE
                # Context
                "source_type": source_type.value,
                "source_details": source_details,
                "ip_address": ip_address,
                "user_agent": user_agent,
                # Request tracking
                "request_id": request_id,
                "session_id": session_id,
                # Multi-tenant
                "institution_id": institution_id,
            }

            # Store audit entry (using database service)
            success = db.create_audit_log(audit_entry)

            if success:
                logger.info(
                    f"Audit log created: {entity_type.value} {entity_id} "
                    f"by {user_email or 'system'}"
                )
                return audit_id
            else:
                logger.error(
                    f"Failed to create audit log for {entity_type.value} {entity_id}"
                )
                return None

        except Exception as e:
            logger.error(f"Audit logging failed for CREATE {entity_type.value}: {e}")
            # Don't let audit failures break the main operation
            return None

    @staticmethod
    def log_update(
        entity_type: EntityType,
        entity_id: str,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        institution_id: Optional[str] = None,
        source_type: SourceType = SourceType.API,
        source_details: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Log entity update

        Args:
            entity_type: Type of entity updated
            entity_id: ID of updated entity
            old_values: Entity state before update
            new_values: Entity state after update
            user_id: User who updated (NULL for system)
            user_email: User email for quick reference
            user_role: User role at time of action
            institution_id: Institution context
            source_type: Where operation originated
            source_details: Additional context
            request_context: Request metadata

        Returns:
            audit_id: ID of created audit log entry
        """
        try:
            audit_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc)

            # Sanitize sensitive data
            sanitized_old = sanitize_for_audit(old_values)
            sanitized_new = sanitize_for_audit(new_values)

            # Determine which fields changed
            changed_fields = get_changed_fields(old_values, new_values)

            # Extract request context
            ip_address = None
            user_agent = None
            request_id = None
            session_id = None

            if request_context:
                ip_address = request_context.get("ip_address")
                user_agent = request_context.get("user_agent")
                request_id = request_context.get("request_id")
                session_id = request_context.get("session_id")

            audit_entry = {
                "audit_id": audit_id,
                "timestamp": timestamp,
                # Who
                "user_id": user_id,
                "user_email": user_email,
                "user_role": user_role,
                # What
                "operation_type": OperationType.UPDATE.value,
                "entity_type": entity_type.value,
                "entity_id": entity_id,
                # Changes
                "old_values": json.dumps(sanitized_old),
                "new_values": json.dumps(sanitized_new),
                "changed_fields": json.dumps(changed_fields),
                # Context
                "source_type": source_type.value,
                "source_details": source_details,
                "ip_address": ip_address,
                "user_agent": user_agent,
                # Request tracking
                "request_id": request_id,
                "session_id": session_id,
                # Multi-tenant
                "institution_id": institution_id,
            }

            # Store audit entry
            success = db.create_audit_log(audit_entry)

            if success:
                logger.info(
                    f"Audit log created: {entity_type.value} {entity_id} "
                    f"updated by {user_email or 'system'} "
                    f"(fields: {', '.join(changed_fields)})"
                )
                return audit_id
            else:
                logger.error(
                    f"Failed to create audit log for {entity_type.value} {entity_id}"
                )
                return None

        except Exception as e:
            logger.error(f"Audit logging failed for UPDATE {entity_type.value}: {e}")
            return None

    @staticmethod
    def log_delete(
        entity_type: EntityType,
        entity_id: str,
        old_values: Dict[str, Any],
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        institution_id: Optional[str] = None,
        source_type: SourceType = SourceType.API,
        source_details: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Log entity deletion

        Args:
            entity_type: Type of entity deleted
            entity_id: ID of deleted entity
            old_values: Entity state before deletion
            user_id: User who deleted (NULL for system)
            user_email: User email for quick reference
            user_role: User role at time of action
            institution_id: Institution context
            source_type: Where operation originated
            source_details: Additional context
            request_context: Request metadata

        Returns:
            audit_id: ID of created audit log entry
        """
        try:
            audit_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc)

            # Sanitize sensitive data
            sanitized_old = sanitize_for_audit(old_values)

            # Extract request context
            ip_address = None
            user_agent = None
            request_id = None
            session_id = None

            if request_context:
                ip_address = request_context.get("ip_address")
                user_agent = request_context.get("user_agent")
                request_id = request_context.get("request_id")
                session_id = request_context.get("session_id")

            audit_entry = {
                "audit_id": audit_id,
                "timestamp": timestamp,
                # Who
                "user_id": user_id,
                "user_email": user_email,
                "user_role": user_role,
                # What
                "operation_type": OperationType.DELETE.value,
                "entity_type": entity_type.value,
                "entity_id": entity_id,
                # Changes
                "old_values": json.dumps(sanitized_old),
                "new_values": None,  # NULL for DELETE
                "changed_fields": None,  # Not applicable for DELETE
                # Context
                "source_type": source_type.value,
                "source_details": source_details,
                "ip_address": ip_address,
                "user_agent": user_agent,
                # Request tracking
                "request_id": request_id,
                "session_id": session_id,
                # Multi-tenant
                "institution_id": institution_id,
            }

            # Store audit entry
            success = db.create_audit_log(audit_entry)

            if success:
                logger.info(
                    f"Audit log created: {entity_type.value} {entity_id} "
                    f"deleted by {user_email or 'system'}"
                )
                return audit_id
            else:
                logger.error(
                    f"Failed to create audit log for {entity_type.value} {entity_id}"
                )
                return None

        except Exception as e:
            logger.error(f"Audit logging failed for DELETE {entity_type.value}: {e}")
            return None

    @staticmethod
    def get_entity_history(
        entity_type: EntityType, entity_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get audit history for specific entity

        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries in chronological order (newest first)
        """
        try:
            return db.get_audit_logs_by_entity(entity_type.value, entity_id, limit)
        except Exception as e:
            logger.error(f"Failed to get entity history: {e}")
            return []

    @staticmethod
    def get_user_activity(
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all activity by specific user

        Args:
            user_id: User ID
            start_date: Filter from this date
            end_date: Filter to this date
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        try:
            return db.get_audit_logs_by_user(user_id, start_date, end_date, limit)
        except Exception as e:
            logger.error(f"Failed to get user activity: {e}")
            return []

    @staticmethod
    def get_recent_activity(
        institution_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent system activity (for dashboard)

        Args:
            institution_id: Filter by institution (NULL = all)
            limit: Maximum number of entries to return

        Returns:
            List of recent audit log entries
        """
        try:
            return db.get_recent_audit_logs(institution_id, limit)
        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}")
            return []

    @staticmethod
    def export_audit_log(
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[EntityType] = None,
        user_id: Optional[str] = None,
        institution_id: Optional[str] = None,
        format_type: str = "csv",
    ) -> bytes:
        """
        Export audit logs for compliance/analysis

        Args:
            start_date: Start of date range
            end_date: End of date range
            entity_type: Filter by entity type (optional)
            user_id: Filter by user (optional)
            institution_id: Filter by institution (optional)
            format_type: Export format ('csv' or 'json')

        Returns:
            Exported data as bytes
        """
        try:
            # Get filtered audit logs
            logs = db.get_audit_logs_filtered(
                start_date=start_date,
                end_date=end_date,
                entity_type=entity_type.value if entity_type else None,
                user_id=user_id,
                institution_id=institution_id,
            )

            if format_type == "csv":
                return _export_as_csv(logs)
            elif format_type == "json":
                return _export_as_json(logs)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")

        except Exception as e:
            logger.error(f"Failed to export audit log: {e}")
            return b""


def _export_as_csv(logs: List[Dict[str, Any]]) -> bytes:
    """Export audit logs as CSV"""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "Timestamp",
            "User Email",
            "User Role",
            "Operation",
            "Entity Type",
            "Entity ID",
            "Changed Fields",
            "Source Type",
            "Institution ID",
        ]
    )

    # Write data rows
    for log in logs:
        writer.writerow(
            [
                log.get("timestamp"),
                log.get("user_email") or "System",
                log.get("user_role"),
                log.get("operation_type"),
                log.get("entity_type"),
                log.get("entity_id"),
                log.get("changed_fields"),
                log.get("source_type"),
                log.get("institution_id"),
            ]
        )

    return output.getvalue().encode("utf-8")


def _export_as_json(logs: List[Dict[str, Any]]) -> bytes:
    """Export audit logs as JSON"""
    return json.dumps(logs, default=str, indent=2).encode("utf-8")
