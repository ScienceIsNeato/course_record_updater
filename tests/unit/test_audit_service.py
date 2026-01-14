"""Unit tests for audit_service.py"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.services.audit_service import (
    AuditService,
    EntityType,
    OperationType,
    SourceType,
    _export_as_csv,
    _export_as_json,
    get_changed_fields,
    sanitize_for_audit,
)


class TestEnums:
    """Test enum definitions"""

    def test_operation_type_enum(self):
        """Test OperationType enum values"""
        assert OperationType.CREATE.value == "CREATE"
        assert OperationType.UPDATE.value == "UPDATE"
        assert OperationType.DELETE.value == "DELETE"

    def test_entity_type_enum(self):
        """Test EntityType enum values"""
        assert EntityType.USER.value == "users"
        assert EntityType.INSTITUTION.value == "institutions"
        assert EntityType.PROGRAM.value == "programs"
        assert EntityType.COURSE.value == "courses"
        assert EntityType.TERM.value == "terms"
        assert EntityType.OFFERING.value == "course_offerings"
        assert EntityType.SECTION.value == "course_sections"
        assert EntityType.OUTCOME.value == "course_outcomes"

    def test_source_type_enum(self):
        """Test SourceType enum values"""
        assert SourceType.API.value == "API"
        assert SourceType.IMPORT.value == "IMPORT"
        assert SourceType.SYSTEM.value == "SYSTEM"
        assert SourceType.SCRIPT.value == "SCRIPT"


class TestSanitizeForAudit:
    """Test sanitize_for_audit function"""

    def test_sanitize_empty_dict(self):
        """Test sanitizing empty dict returns empty dict"""
        result = sanitize_for_audit({})
        assert result == {}

    def test_sanitize_none_returns_empty(self):
        """Test sanitizing None returns empty dict"""
        result = sanitize_for_audit(None)
        assert result == {}

    def test_sanitize_password_field(self):
        """Test password field is redacted"""
        data = {"email": "test@example.com", "password": "secret123"}
        result = sanitize_for_audit(data)
        assert result["email"] == "test@example.com"
        assert result["password"] == "[REDACTED]"

    def test_sanitize_multiple_sensitive_fields(self):
        """Test multiple sensitive fields are redacted"""
        data = {
            "email": "test@example.com",
            "password": "secret123",
            "password_hash": "hash123",
            "api_key": "key123",
            "oauth_token": "token123",
        }
        result = sanitize_for_audit(data)
        assert result["email"] == "test@example.com"
        assert result["password"] == "[REDACTED]"
        assert result["password_hash"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["oauth_token"] == "[REDACTED]"

    def test_sanitize_preserves_normal_fields(self):
        """Test normal fields are not modified"""
        data = {
            "user_id": "user-123",
            "first_name": "John",
            "last_name": "Doe",
            "role": "instructor",
        }
        result = sanitize_for_audit(data)
        assert result == data


class TestGetChangedFields:
    """Test get_changed_fields function"""

    def test_empty_dicts_returns_empty_list(self):
        """Test empty dicts return empty list"""
        result = get_changed_fields({}, {})
        assert result == []

    def test_none_old_values_returns_empty(self):
        """Test None old values returns empty list"""
        result = get_changed_fields(None, {"name": "New"})
        assert result == []

    def test_none_new_values_returns_empty(self):
        """Test None new values returns empty list"""
        result = get_changed_fields({"name": "Old"}, None)
        assert result == []

    def test_no_changes_returns_empty_list(self):
        """Test identical dicts return empty list"""
        data = {"name": "John", "email": "john@example.com"}
        result = get_changed_fields(data, data)
        assert result == []

    def test_single_field_changed(self):
        """Test single field change is detected"""
        old = {"name": "John", "email": "john@example.com"}
        new = {"name": "Jane", "email": "john@example.com"}
        result = get_changed_fields(old, new)
        assert "name" in result
        assert "email" not in result

    def test_multiple_fields_changed(self):
        """Test multiple field changes are detected"""
        old = {"name": "John", "email": "john@example.com", "role": "instructor"}
        new = {"name": "Jane", "email": "jane@example.com", "role": "instructor"}
        result = get_changed_fields(old, new)
        assert "name" in result
        assert "email" in result
        assert "role" not in result

    def test_new_field_added(self):
        """Test new field is detected as change"""
        old = {"name": "John"}
        new = {"name": "John", "email": "john@example.com"}
        result = get_changed_fields(old, new)
        assert "email" in result

    def test_field_removed(self):
        """Test removed field is detected as change"""
        old = {"name": "John", "email": "john@example.com"}
        new = {"name": "John"}
        result = get_changed_fields(old, new)
        assert "email" in result

    def test_datetime_comparison_ignores_microseconds(self):
        """Test datetime comparison ignores microseconds"""
        dt1 = datetime(2025, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 1, 12, 0, 0, 654321, tzinfo=timezone.utc)
        old = {"created_at": dt1}
        new = {"created_at": dt2}
        result = get_changed_fields(old, new)
        # Should be empty because we ignore microseconds
        assert result == []

    def test_datetime_different_seconds_detected(self):
        """Test datetime with different seconds is detected"""
        dt1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
        old = {"created_at": dt1}
        new = {"created_at": dt2}
        result = get_changed_fields(old, new)
        assert "created_at" in result


class TestAuditServiceLogCreate:
    """Test AuditService.log_create method"""

    @patch("src.services.audit_service.db")
    @patch("src.services.audit_service.uuid.uuid4")
    def test_log_create_success(self, mock_uuid, mock_db):
        """Test successful create log"""
        mock_uuid.return_value = MagicMock(hex="audit-123")
        mock_db.create_audit_log.return_value = True

        result = AuditService.log_create(
            entity_type=EntityType.USER,
            entity_id="user-123",
            new_values={"email": "test@example.com", "role": "instructor"},
            user_id="admin-123",
            user_email="admin@example.com",
            user_role="site_admin",
            institution_id="inst-1",
            source_type=SourceType.API,
        )

        assert result is not None
        mock_db.create_audit_log.assert_called_once()
        call_args = mock_db.create_audit_log.call_args[0][0]
        assert call_args["operation_type"] == "CREATE"
        assert call_args["entity_type"] == "users"
        assert call_args["entity_id"] == "user-123"
        assert call_args["old_values"] is None
        assert json.loads(call_args["new_values"])["email"] == "test@example.com"

    @patch("src.services.audit_service.db")
    @patch("src.services.audit_service.uuid.uuid4")
    def test_log_create_sanitizes_sensitive_data(self, mock_uuid, mock_db):
        """Test create log sanitizes sensitive fields"""
        mock_uuid.return_value = MagicMock(hex="audit-123")
        mock_db.create_audit_log.return_value = True

        AuditService.log_create(
            entity_type=EntityType.USER,
            entity_id="user-123",
            new_values={"email": "test@example.com", "password": "secret123"},
            user_id="admin-123",
        )

        call_args = mock_db.create_audit_log.call_args[0][0]
        new_values = json.loads(call_args["new_values"])
        assert new_values["password"] == "[REDACTED]"

    @patch("src.services.audit_service.db")
    @patch("src.services.audit_service.uuid.uuid4")
    def test_log_create_with_request_context(self, mock_uuid, mock_db):
        """Test create log includes request context"""
        mock_uuid.return_value = MagicMock(hex="audit-123")
        mock_db.create_audit_log.return_value = True

        request_context = {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "request_id": "req-123",
            "session_id": "sess-123",
        }

        AuditService.log_create(
            entity_type=EntityType.USER,
            entity_id="user-123",
            new_values={"email": "test@example.com"},
            request_context=request_context,
        )

        call_args = mock_db.create_audit_log.call_args[0][0]
        assert call_args["ip_address"] == "192.168.1.1"
        assert call_args["user_agent"] == "Mozilla/5.0"
        assert call_args["request_id"] == "req-123"
        assert call_args["session_id"] == "sess-123"

    @patch("src.services.audit_service.db")
    def test_log_create_db_failure_returns_none(self, mock_db):
        """Test create log returns None on database failure"""
        mock_db.create_audit_log.return_value = False

        result = AuditService.log_create(
            entity_type=EntityType.USER,
            entity_id="user-123",
            new_values={"email": "test@example.com"},
        )

        assert result is None

    @patch("src.services.audit_service.db")
    def test_log_create_exception_returns_none(self, mock_db):
        """Test create log returns None on exception"""
        mock_db.create_audit_log.side_effect = Exception("Database error")

        result = AuditService.log_create(
            entity_type=EntityType.USER,
            entity_id="user-123",
            new_values={"email": "test@example.com"},
        )

        assert result is None


class TestAuditServiceLogUpdate:
    """Test AuditService.log_update method"""

    @patch("src.services.audit_service.db")
    @patch("src.services.audit_service.uuid.uuid4")
    def test_log_update_success(self, mock_uuid, mock_db):
        """Test successful update log"""
        mock_uuid.return_value = MagicMock(hex="audit-123")
        mock_db.create_audit_log.return_value = True

        old_values = {"email": "old@example.com", "role": "instructor"}
        new_values = {"email": "new@example.com", "role": "instructor"}

        result = AuditService.log_update(
            entity_type=EntityType.USER,
            entity_id="user-123",
            old_values=old_values,
            new_values=new_values,
            user_id="admin-123",
            user_email="admin@example.com",
        )

        assert result is not None
        mock_db.create_audit_log.assert_called_once()
        call_args = mock_db.create_audit_log.call_args[0][0]
        assert call_args["operation_type"] == "UPDATE"
        assert call_args["entity_id"] == "user-123"
        changed = json.loads(call_args["changed_fields"])
        assert "email" in changed
        assert "role" not in changed

    @patch("src.services.audit_service.db")
    @patch("src.services.audit_service.uuid.uuid4")
    def test_log_update_sanitizes_both_states(self, mock_uuid, mock_db):
        """Test update log sanitizes both old and new values"""
        mock_uuid.return_value = MagicMock(hex="audit-123")
        mock_db.create_audit_log.return_value = True

        old_values = {"email": "test@example.com", "password": "old_secret"}
        new_values = {"email": "test@example.com", "password": "new_secret"}

        AuditService.log_update(
            entity_type=EntityType.USER,
            entity_id="user-123",
            old_values=old_values,
            new_values=new_values,
        )

        call_args = mock_db.create_audit_log.call_args[0][0]
        old = json.loads(call_args["old_values"])
        new = json.loads(call_args["new_values"])
        assert old["password"] == "[REDACTED]"
        assert new["password"] == "[REDACTED]"

    @patch("src.services.audit_service.db")
    def test_log_update_exception_returns_none(self, mock_db):
        """Test update log returns None on exception"""
        mock_db.create_audit_log.side_effect = Exception("Database error")

        result = AuditService.log_update(
            entity_type=EntityType.USER,
            entity_id="user-123",
            old_values={"email": "old@example.com"},
            new_values={"email": "new@example.com"},
        )

        assert result is None


class TestAuditServiceLogDelete:
    """Test AuditService.log_delete method"""

    @patch("src.services.audit_service.db")
    @patch("src.services.audit_service.uuid.uuid4")
    def test_log_delete_success(self, mock_uuid, mock_db):
        """Test successful delete log"""
        mock_uuid.return_value = MagicMock(hex="audit-123")
        mock_db.create_audit_log.return_value = True

        old_values = {"email": "test@example.com", "role": "instructor"}

        result = AuditService.log_delete(
            entity_type=EntityType.USER,
            entity_id="user-123",
            old_values=old_values,
            user_id="admin-123",
            user_email="admin@example.com",
        )

        assert result is not None
        mock_db.create_audit_log.assert_called_once()
        call_args = mock_db.create_audit_log.call_args[0][0]
        assert call_args["operation_type"] == "DELETE"
        assert call_args["entity_id"] == "user-123"
        assert call_args["new_values"] is None
        assert call_args["changed_fields"] is None
        assert json.loads(call_args["old_values"])["email"] == "test@example.com"

    @patch("src.services.audit_service.db")
    @patch("src.services.audit_service.uuid.uuid4")
    def test_log_delete_sanitizes_old_values(self, mock_uuid, mock_db):
        """Test delete log sanitizes old values"""
        mock_uuid.return_value = MagicMock(hex="audit-123")
        mock_db.create_audit_log.return_value = True

        old_values = {"email": "test@example.com", "password": "secret123"}

        AuditService.log_delete(
            entity_type=EntityType.USER, entity_id="user-123", old_values=old_values
        )

        call_args = mock_db.create_audit_log.call_args[0][0]
        old = json.loads(call_args["old_values"])
        assert old["password"] == "[REDACTED]"

    @patch("src.services.audit_service.db")
    def test_log_delete_exception_returns_none(self, mock_db):
        """Test delete log returns None on exception"""
        mock_db.create_audit_log.side_effect = Exception("Database error")

        result = AuditService.log_delete(
            entity_type=EntityType.USER,
            entity_id="user-123",
            old_values={"email": "test@example.com"},
        )

        assert result is None


class TestAuditServiceQueryMethods:
    """Test AuditService query methods"""

    @patch("src.services.audit_service.db")
    def test_get_entity_history_success(self, mock_db):
        """Test get_entity_history returns logs"""
        mock_logs = [
            {"audit_id": "1", "operation_type": "CREATE"},
            {"audit_id": "2", "operation_type": "UPDATE"},
        ]
        mock_db.get_audit_logs_by_entity.return_value = mock_logs

        result = AuditService.get_entity_history(EntityType.USER, "user-123", limit=10)

        assert result == mock_logs
        mock_db.get_audit_logs_by_entity.assert_called_once_with(
            "users", "user-123", 10
        )

    @patch("src.services.audit_service.db")
    def test_get_entity_history_exception_returns_empty(self, mock_db):
        """Test get_entity_history returns empty list on exception"""
        mock_db.get_audit_logs_by_entity.side_effect = Exception("Database error")

        result = AuditService.get_entity_history(EntityType.USER, "user-123")

        assert result == []

    @patch("src.services.audit_service.db")
    def test_get_user_activity_success(self, mock_db):
        """Test get_user_activity returns logs"""
        mock_logs = [{"audit_id": "1", "entity_type": "users"}]
        mock_db.get_audit_logs_by_user.return_value = mock_logs

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        result = AuditService.get_user_activity(
            "user-123", start_date=start_date, end_date=end_date, limit=50
        )

        assert result == mock_logs
        mock_db.get_audit_logs_by_user.assert_called_once_with(
            "user-123", start_date, end_date, 50
        )

    @patch("src.services.audit_service.db")
    def test_get_user_activity_exception_returns_empty(self, mock_db):
        """Test get_user_activity returns empty list on exception"""
        mock_db.get_audit_logs_by_user.side_effect = Exception("Database error")

        result = AuditService.get_user_activity("user-123")

        assert result == []

    @patch("src.services.audit_service.db")
    def test_get_recent_activity_success(self, mock_db):
        """Test get_recent_activity returns logs"""
        mock_logs = [{"audit_id": "1"}, {"audit_id": "2"}]
        mock_db.get_recent_audit_logs.return_value = mock_logs

        result = AuditService.get_recent_activity(institution_id="inst-1", limit=25)

        assert result == mock_logs
        mock_db.get_recent_audit_logs.assert_called_once_with("inst-1", 25)

    @patch("src.services.audit_service.db")
    def test_get_recent_activity_exception_returns_empty(self, mock_db):
        """Test get_recent_activity returns empty list on exception"""
        mock_db.get_recent_audit_logs.side_effect = Exception("Database error")

        result = AuditService.get_recent_activity()

        assert result == []


class TestAuditServiceExport:
    """Test AuditService.export_audit_log method"""

    @patch("src.services.audit_service.db")
    def test_export_as_csv_success(self, mock_db):
        """Test export as CSV"""
        mock_logs = [
            {
                "timestamp": "2025-01-01T12:00:00",
                "user_email": "admin@example.com",
                "user_role": "site_admin",
                "operation_type": "CREATE",
                "entity_type": "users",
                "entity_id": "user-123",
                "changed_fields": None,
                "source_type": "API",
                "institution_id": "inst-1",
            }
        ]
        mock_db.get_audit_logs_filtered.return_value = mock_logs

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        result = AuditService.export_audit_log(
            start_date=start_date, end_date=end_date, format_type="csv"
        )

        assert isinstance(result, bytes)
        decoded = result.decode("utf-8")
        assert "Timestamp" in decoded
        assert "admin@example.com" in decoded
        assert "CREATE" in decoded

    @patch("src.services.audit_service.db")
    def test_export_as_json_success(self, mock_db):
        """Test export as JSON"""
        mock_logs = [
            {
                "audit_id": "audit-123",
                "operation_type": "CREATE",
                "entity_type": "users",
            }
        ]
        mock_db.get_audit_logs_filtered.return_value = mock_logs

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        result = AuditService.export_audit_log(
            start_date=start_date, end_date=end_date, format_type="json"
        )

        assert isinstance(result, bytes)
        decoded = json.loads(result.decode("utf-8"))
        assert len(decoded) == 1
        assert decoded[0]["audit_id"] == "audit-123"

    @patch("src.services.audit_service.db")
    def test_export_with_filters(self, mock_db):
        """Test export with entity and user filters"""
        mock_db.get_audit_logs_filtered.return_value = []

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        AuditService.export_audit_log(
            start_date=start_date,
            end_date=end_date,
            entity_type=EntityType.USER,
            user_id="user-123",
            institution_id="inst-1",
            format_type="csv",
        )

        mock_db.get_audit_logs_filtered.assert_called_once_with(
            start_date=start_date,
            end_date=end_date,
            entity_type="users",
            user_id="user-123",
            institution_id="inst-1",
        )

    @patch("src.services.audit_service.db")
    def test_export_unsupported_format_returns_empty(self, mock_db):
        """Test export with unsupported format returns empty bytes"""
        mock_db.get_audit_logs_filtered.return_value = []

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        result = AuditService.export_audit_log(
            start_date=start_date, end_date=end_date, format_type="xml"
        )

        assert result == b""

    @patch("src.services.audit_service.db")
    def test_export_exception_returns_empty(self, mock_db):
        """Test export returns empty bytes on exception"""
        mock_db.get_audit_logs_filtered.side_effect = Exception("Database error")

        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 31, tzinfo=timezone.utc)

        result = AuditService.export_audit_log(
            start_date=start_date, end_date=end_date, format_type="csv"
        )

        assert result == b""


class TestExportHelpers:
    """Test export helper functions"""

    def test_export_as_csv_format(self):
        """Test CSV export format"""
        logs = [
            {
                "timestamp": "2025-01-01T12:00:00",
                "user_email": "admin@example.com",
                "user_role": "site_admin",
                "operation_type": "CREATE",
                "entity_type": "users",
                "entity_id": "user-123",
                "changed_fields": '["email"]',
                "source_type": "API",
                "institution_id": "inst-1",
            }
        ]

        result = _export_as_csv(logs)
        decoded = result.decode("utf-8")

        lines = decoded.strip().split("\n")
        assert len(lines) == 2  # Header + 1 data row
        assert "Timestamp" in lines[0]
        assert "admin@example.com" in lines[1]

    def test_export_as_csv_system_user(self):
        """Test CSV export shows 'System' for null user email"""
        logs = [
            {
                "timestamp": "2025-01-01T12:00:00",
                "user_email": None,
                "user_role": None,
                "operation_type": "CREATE",
                "entity_type": "users",
                "entity_id": "user-123",
                "changed_fields": None,
                "source_type": "SYSTEM",
                "institution_id": "inst-1",
            }
        ]

        result = _export_as_csv(logs)
        decoded = result.decode("utf-8")

        assert "System" in decoded

    def test_export_as_json_format(self):
        """Test JSON export format"""
        logs = [
            {"audit_id": "audit-123", "operation_type": "CREATE"},
            {"audit_id": "audit-456", "operation_type": "UPDATE"},
        ]

        result = _export_as_json(logs)
        decoded = json.loads(result.decode("utf-8"))

        assert len(decoded) == 2
        assert decoded[0]["audit_id"] == "audit-123"
        assert decoded[1]["audit_id"] == "audit-456"

    def test_export_as_json_empty_list(self):
        """Test JSON export with empty list"""
        result = _export_as_json([])
        decoded = json.loads(result.decode("utf-8"))

        assert decoded == []
