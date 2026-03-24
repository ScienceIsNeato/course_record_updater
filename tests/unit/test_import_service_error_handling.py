"""Error handling tests for ImportService."""

from typing import Any

from src.services.import_service import ConflictStrategy, ImportService


class TestImportServiceErrorHandling:
    """Test error handling in ImportService."""

    def test_prepare_import_adapter_registry_error(self) -> None:
        """Test _prepare_import handles AdapterRegistryError."""
        from unittest.mock import patch

        from src.adapters.adapter_registry import AdapterRegistryError

        service = ImportService("test_inst")
        service.reset_stats()

        with patch("src.services.import_service.get_adapter_registry") as mock_registry:
            mock_reg = mock_registry.return_value
            mock_reg.get_adapter_by_id.side_effect = AdapterRegistryError(
                "Registry failed"
            )

            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(b"test")
                tmp_path = tmp.name

            try:
                result = service._prepare_import(tmp_path, "test_adapter")

                assert result is None
                assert len(service.stats["errors"]) > 0
                assert "Failed to get adapter" in service.stats["errors"][0]
                assert "Registry failed" in service.stats["errors"][0]
            finally:
                os.unlink(tmp_path)

    def test_prepare_import_file_validation_exception(self) -> None:
        """Test _prepare_import handles file validation exception."""
        from unittest.mock import Mock, patch

        service = ImportService("test_inst")
        service.reset_stats()

        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.side_effect = RuntimeError(
            "Validation failed"
        )

        with patch("src.services.import_service.get_adapter_registry") as mock_registry:
            mock_reg = mock_registry.return_value
            mock_reg.get_adapter_by_id.return_value = mock_adapter

            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(b"test")
                tmp_path = tmp.name

            try:
                result = service._prepare_import(tmp_path, "test_adapter")

                assert result is None
                assert len(service.stats["errors"]) > 0
                assert "File validation failed" in service.stats["errors"][0]
                assert "Validation failed" in service.stats["errors"][0]
            finally:
                os.unlink(tmp_path)

    def test_update_progress_with_callback(self) -> None:
        """Test _update_progress calls progress_callback when set."""
        from unittest.mock import Mock

        service = ImportService("test_inst")
        service.reset_stats()

        mock_callback = Mock()
        service.progress_callback = mock_callback

        service._update_progress(50, 100, "courses")

        assert mock_callback.called
        call_args = mock_callback.call_args[1]
        assert call_args["percentage"] == 50
        assert call_args["records_processed"] == 50
        assert call_args["total_records"] == 100
        assert "courses" in call_args["message"]

    def test_process_single_record_offerings(self) -> None:
        """Test _process_single_record handles offerings."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        with patch.object(service, "_process_offering_import") as mock_process:
            conflicts = service._process_single_record(
                "offerings",
                {"offering_id": "test"},
                ConflictStrategy.USE_THEIRS,
                dry_run=False,
            )

            assert conflicts == []
            assert mock_process.called

    def test_process_single_record_sections(self) -> None:
        """Test _process_single_record handles sections."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        with patch.object(service, "_process_section_import") as mock_process:
            conflicts = service._process_single_record(
                "sections",
                {"section_id": "test"},
                ConflictStrategy.USE_THEIRS,
                dry_run=False,
            )

            assert conflicts == []
            assert mock_process.called

    def test_process_single_record_terms(self) -> None:
        """Test _process_single_record handles terms."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        with patch.object(service, "_process_term_import") as mock_process:
            conflicts = service._process_single_record(
                "terms", {"term_id": "test"}, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert conflicts == []
            assert mock_process.called

    def test_resolve_user_conflicts_use_theirs_dry_run(self) -> None:
        """Test _resolve_user_conflicts with USE_THEIRS strategy in dry run."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        user_data = {"email": "test@example.com", "first_name": "Test"}
        existing_user = {"email": "test@example.com", "first_name": "Old"}
        detected_conflicts: list[Any] = []

        with patch("src.services.import_service.update_user") as mock_update:
            service._resolve_user_conflicts(
                ConflictStrategy.USE_THEIRS,
                detected_conflicts,
                user_data,
                existing_user,
                "test@example.com",
                dry_run=True,
                conflicts=[],
            )

            assert not mock_update.called
            assert service.stats["records_updated"] == 0

    def test_import_excel_file_top_level_exception(self) -> None:
        """Test import_excel_file handles unexpected top-level exception."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        with patch.object(service, "_prepare_import", side_effect=RuntimeError("Boom")):
            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(b"test")
                tmp_path = tmp.name

            try:
                result = service.import_excel_file(tmp_path)

                assert result.success is False
                assert len(result.errors) > 0
                assert "Unexpected error during import" in result.errors[0]
                assert "Boom" in result.errors[0]
            finally:
                os.unlink(tmp_path)

    def test_process_data_records_exception_handling(self) -> None:
        """Test exception handling when processing individual records in a batch."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        with patch.object(
            service,
            "_process_single_record",
            side_effect=RuntimeError("Record processing failed"),
        ):
            conflicts = service._process_data_type_records(
                "courses",
                [{"course_number": "TEST-101"}],
                ConflictStrategy.USE_THEIRS,
                False,
                0,
                1,
            )

            assert len(service.stats["errors"]) > 0
            assert "Error processing courses record" in service.stats["errors"][0]
            assert "Record processing failed" in service.stats["errors"][0]

    def test_process_single_record_unknown_type(self) -> None:
        """Test _process_single_record with unknown data type returns empty list."""
        service = ImportService("test_inst")
        service.reset_stats()

        conflicts = service._process_single_record(
            "unknown_type", {"data": "test"}, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        assert conflicts == []

    def test_resolve_user_conflicts_use_mine_with_conflicts(self) -> None:
        """Test _resolve_user_conflicts with USE_MINE and detected conflicts."""
        service = ImportService("test_inst")
        service.reset_stats()

        from datetime import datetime, timezone

        from src.services.import_service import ConflictRecord

        detected_conflicts = [
            ConflictRecord(
                entity_type="user",
                entity_id="test@example.com",
                field_name="first_name",
                existing_value="Old",
                import_value="New",
                resolution="pending",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        service._resolve_user_conflicts(
            ConflictStrategy.USE_MINE,
            detected_conflicts,
            {"email": "test@example.com"},
            {"email": "test@example.com"},
            "test@example.com",
            dry_run=False,
            conflicts=[],
        )

        assert service.stats["conflicts_resolved"] == 1
        assert detected_conflicts[0].resolution == "use_mine"

    def test_resolve_course_conflicts_use_theirs_dry_run(self) -> None:
        """Test _resolve_course_conflicts with USE_THEIRS in dry run mode."""
        service = ImportService("test_inst")
        service.reset_stats()

        from datetime import datetime, timezone

        from src.services.import_service import ConflictRecord

        detected_conflicts = [
            ConflictRecord(
                entity_type="course",
                entity_id="MATH-101",
                field_name="title",
                existing_value="Algebra",
                import_value="New Algebra",
                resolution="pending",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        course_data = {"course_number": "MATH-101", "course_title": "New Algebra"}
        existing_course = {
            "course_id": "course_123",
            "course_number": "MATH-101",
            "course_title": "Algebra",
        }

        service._resolve_course_conflicts(
            ConflictStrategy.USE_THEIRS,
            detected_conflicts,
            course_data,
            existing_course,
            "MATH-101",
            dry_run=True,
        )

        assert service.stats["conflicts_resolved"] == 1
