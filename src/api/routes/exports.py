"""
Export API routes.

Provides endpoints for exporting data and retrieving available adapters.
Supports institution-specific and system-wide (Site Admin) exports.
"""

import json
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import Blueprint, after_this_request, jsonify, request, send_file
from flask.typing import ResponseReturnValue

from src.api.utils import (
    DEFAULT_EXPORT_EXTENSION,
    get_current_user_safe,
    get_mimetype_for_extension,
)
from src.database.database_service import get_all_institutions
from src.services.auth_service import UserRole, login_required
from src.services.export_service import ExportConfig, create_export_service
from src.utils.constants import USER_NOT_AUTHENTICATED_MSG
from src.utils.logging_config import get_logger

# Create blueprint
exports_bp = Blueprint("exports", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)

# Local constant matching the monolith's private constant
_DEFAULT_EXPORT_EXTENSION = DEFAULT_EXPORT_EXTENSION


@exports_bp.route("/adapters", methods=["GET"])
@login_required
def get_available_adapters() -> ResponseReturnValue:
    """
    Get available adapters for the current user based on their role and institution scope.

    Returns:
        JSON response with list of available adapters
    """
    try:
        from src.adapters.adapter_registry import get_adapter_registry

        current_user = get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": USER_NOT_AUTHENTICATED_MSG}), 401

        registry = get_adapter_registry()
        user_role = current_user.get("role")
        if not user_role or not isinstance(user_role, str):
            return jsonify({"success": False, "error": "User role missing"}), 401
        user_institution_id = current_user.get("institution_id")
        if not user_institution_id or not isinstance(user_institution_id, str):
            return jsonify({"success": False, "error": "Institution ID missing"}), 401
        adapters = registry.get_adapters_for_user(user_role, user_institution_id)

        # Format adapters for frontend consumption
        adapter_list = []
        for adapter_info in adapters:
            adapter_list.append(
                {
                    "id": adapter_info["id"],
                    "name": adapter_info["name"],
                    "description": adapter_info["description"],
                    "institution_id": adapter_info.get(
                        "institution_id"
                    ),  # Use .get() for safety
                    "supported_formats": adapter_info["supported_formats"],
                    "data_types": adapter_info["data_types"],
                }
            )

        return jsonify({"success": True, "adapters": adapter_list})

    except Exception as e:
        logger.error(f"Error getting available adapters: {str(e)}")
        return (
            jsonify(
                {"success": False, "error": "Failed to retrieve available adapters"}
            ),
            500,
        )


@exports_bp.route("/export/data", methods=["GET"])
@login_required
def export_data() -> ResponseReturnValue:
    """
    Export data using institution-specific adapter.

    Query parameters:
        - export_data_type: Type of data to export (courses, users, sections, etc.)
        - export_adapter: Adapter to use - adapter determines file format
        - include_metadata: Include metadata (true/false) - defaults to true
        - anonymize_data: Anonymize personal info (true/false) - defaults to false

    Site Admin Behavior:
        - Exports ALL institutions as a zip containing subdirectories per institution
        - Structure: system_export_TIMESTAMP.zip
                       ├── system_manifest.json
                       ├── mocku/
                       │   └── [institution export files]
                       ├── rcc/
                       │   └── [institution export files]
                       └── ptu/
                           └── [institution export files]
    """
    try:
        current_user = get_current_user_safe()
        if not current_user:
            logger.error("[EXPORT] User not authenticated")
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        user_role = current_user.get("role")
        institution_id = current_user.get("institution_id")

        # Site Admin: Export all institutions
        if user_role == UserRole.SITE_ADMIN.value:
            logger.info("[EXPORT] Site Admin export - exporting all institutions")
            return _export_all_institutions(current_user)

        # Other roles: Export single institution
        if not institution_id:
            logger.error(
                f"[EXPORT] No institution_id for user: {current_user.get('email')}"
            )
            return jsonify({"success": False, "error": "No institution context"}), 400

        # Get parameters
        data_type_raw = request.args.get("export_data_type", "courses")
        adapter_id_raw = request.args.get("export_adapter", "cei_excel_format_v1")

        # Sanitize data_type to prevent path traversal (security fix for S2083)
        # Only allow alphanumeric characters and underscores
        data_type = re.sub(r"\W", "", data_type_raw)
        if not data_type:
            data_type = "courses"  # Fallback to safe default

        # Sanitize adapter_id to prevent log injection (security fix for S5145)
        # Only allow alphanumeric characters, underscores, and hyphens
        adapter_id = re.sub(r"[^a-zA-Z0-9_-]", "", adapter_id_raw)
        if not adapter_id:
            adapter_id = "cei_excel_format_v1"  # Fallback to safe default

        logger.info(
            f"[EXPORT] Request: institution_id={institution_id}, data_type={data_type}, adapter={adapter_id}"
        )
        include_metadata = (
            request.args.get("include_metadata", "true").lower() == "true"
        )

        # Create export service and get adapter info
        export_service = create_export_service()

        # Query adapter for its supported format
        try:
            adapter = export_service.registry.get_adapter_by_id(adapter_id)
            if not adapter:
                logger.error(f"[EXPORT] Adapter not found: {adapter_id}")
                return (
                    jsonify(
                        {"success": False, "error": f"Adapter not found: {adapter_id}"}
                    ),
                    400,
                )

            adapter_info = adapter.get_adapter_info()
            supported_formats = adapter_info.get(
                "supported_formats", [_DEFAULT_EXPORT_EXTENSION]
            )
            # Use first supported format from adapter
            file_extension = (
                supported_formats[0] if supported_formats else _DEFAULT_EXPORT_EXTENSION
            )
        except Exception as adapter_error:
            logger.error(f"[EXPORT] Error getting adapter info: {str(adapter_error)}")
            # Fallback to xlsx if adapter query fails
            file_extension = _DEFAULT_EXPORT_EXTENSION

        # Determine output format from file extension (remove leading dot)
        output_format = (
            file_extension.lstrip(".")
            if file_extension.startswith(".")
            else file_extension
        )

        # Create export config
        config = ExportConfig(
            institution_id=institution_id,
            adapter_id=adapter_id,
            export_view="standard",
            include_metadata=include_metadata,
            output_format=output_format,
        )

        # Create temp file for export in secure temp directory
        temp_dir = Path(tempfile.gettempdir())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # filename now uses sanitized data_type and adapter-determined extension
        filename = f"{data_type}_export_{timestamp}{file_extension}"
        output_path = temp_dir / filename

        # Verify output path is within temp directory (defense in depth)
        # Resolve parent directory first since output file doesn't exist yet
        resolved_output_parent = output_path.parent.resolve()
        resolved_temp_dir = temp_dir.resolve()
        if not str(resolved_output_parent).startswith(str(resolved_temp_dir)):
            logger.error(f"[EXPORT] Path traversal attempt detected: {output_path}")
            return jsonify({"success": False, "error": "Invalid export path"}), 400

        # Perform export
        result = export_service.export_data(config, str(output_path))

        if not result.success:
            logger.error(f"[EXPORT] Export failed: {result.errors}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Export failed",
                        "details": result.errors,
                    }
                ),
                500,
            )

        logger.info(
            f"[EXPORT] Export successful: {result.records_exported} records, file: {result.file_path}"
        )

        # Get appropriate mimetype from adapter's file extension
        mimetype = get_mimetype_for_extension(file_extension)

        # Schedule temp file cleanup after response is sent
        file_to_cleanup = output_path  # Capture for closure

        @after_this_request
        def cleanup_temp_file(response: Any) -> Any:
            try:
                if file_to_cleanup.exists():
                    file_to_cleanup.unlink()
                    logger.debug(f"[EXPORT] Cleaned up temp file: {file_to_cleanup}")
            except Exception as cleanup_error:
                logger.warning(f"[EXPORT] Failed to cleanup temp file: {cleanup_error}")
            return response

        # Send file as download
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype,
        )

    except Exception as e:
        logger.error(f"Error during export: {str(e)}", exc_info=True)
        # Sanitize error message to avoid leaking internal details
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Export failed. Please try again or contact support.",
                }
            ),
            500,
        )


def _sanitize_export_params() -> Tuple[str, str, bool]:
    """Extract and sanitize export parameters from request."""
    data_type_raw = request.args.get("export_data_type", "courses")
    adapter_id_raw = request.args.get("export_adapter", "generic_csv_v1")

    # Sanitize parameters (allow alphanumeric, underscore, hyphen, and dot)
    data_type = re.sub(r"[^\w.-]", "", data_type_raw) or "courses"
    adapter_id = re.sub(r"[^\w.-]", "", adapter_id_raw) or "generic_csv_v1"
    include_metadata = request.args.get("include_metadata", "true").lower() == "true"

    return data_type, adapter_id, include_metadata


def _get_adapter_file_extension(export_service: Any, adapter_id: str) -> str:
    """Get file extension from adapter, with fallback to default."""
    try:
        adapter = export_service.registry.get_adapter_by_id(adapter_id)
        if not adapter:
            return _DEFAULT_EXPORT_EXTENSION

        adapter_info = adapter.get_adapter_info()
        supported_formats = adapter_info.get(
            "supported_formats", [_DEFAULT_EXPORT_EXTENSION]
        )
        return supported_formats[0] if supported_formats else _DEFAULT_EXPORT_EXTENSION
    except Exception as adapter_error:
        logger.error(f"[EXPORT] Error getting adapter info: {str(adapter_error)}")
        return _DEFAULT_EXPORT_EXTENSION


def _export_institution(
    export_service: Any,
    inst: Dict[str, Any],
    system_export_dir: Path,
    adapter_id: str,
    include_metadata: bool,
    output_format: str,
    data_type: str,
    timestamp: str,
    file_extension: str,
) -> Dict[str, Any]:
    """Export a single institution to its subdirectory."""
    inst_id = inst.get("institution_id") or "unknown"
    inst_short_name = inst.get("short_name") or inst_id

    # Create subdirectory for this institution
    inst_dir = system_export_dir / inst_short_name
    inst_dir.mkdir(exist_ok=True)

    logger.info(f"[EXPORT] Exporting institution: {inst_short_name} ({inst_id})")

    # Create export config for this institution
    config = ExportConfig(
        institution_id=inst_id,
        adapter_id=adapter_id,
        export_view="standard",
        include_metadata=include_metadata,
        output_format=output_format,
    )

    # Export to institution directory
    inst_filename = f"{data_type}_export_{timestamp}{file_extension}"
    inst_output_path = inst_dir / inst_filename
    result = export_service.export_data(config, str(inst_output_path))

    if not result.success:
        logger.warning(f"[EXPORT] Failed to export {inst_short_name}: {result.errors}")

    return {
        "institution_id": inst_id,
        "institution_name": inst.get("name"),
        "short_name": inst_short_name,
        "success": result.success,
        "records_exported": result.records_exported,
        "file": inst_filename,
        "errors": result.errors if not result.success else [],
    }


def _create_system_export_zip(
    system_export_dir: Path, temp_base: Path, timestamp: str, unique_id: str
) -> Path:
    """Create ZIP file from system export directory, excluding system files."""
    import zipfile

    system_zip_path = temp_base / f"system_export_{timestamp}_{unique_id}.zip"
    excluded_patterns = {".DS_Store", "__MACOSX", ".git", "Thumbs.db"}

    with zipfile.ZipFile(system_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in system_export_dir.rglob("*"):
            if any(pattern in file_path.parts for pattern in excluded_patterns):
                continue
            if file_path.is_file():
                arcname = file_path.relative_to(system_export_dir)
                zipf.write(file_path, arcname)

    return system_zip_path


def _create_system_manifest(
    current_user: Dict[str, Any],
    timestamp: str,
    adapter_id: str,
    data_type: str,
    institutions: List[Dict[str, Any]],
    institution_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create system-level export manifest with export metadata."""
    return {
        "format_version": "1.0",
        "export_type": "system_wide",
        "export_timestamp": timestamp,
        "exported_by": current_user.get("email"),
        "adapter_id": adapter_id,
        "data_type": data_type,
        "total_institutions": len(institutions),
        "successful_exports": sum(1 for r in institution_results if r["success"]),
        "failed_exports": sum(1 for r in institution_results if not r["success"]),
        "institutions": institution_results,
    }


def _export_all_institutions(current_user: Dict[str, Any]) -> ResponseReturnValue:
    """
    Export all institutions for Site Admin as a zip of folders.

    Creates structure:
        system_export_TIMESTAMP.zip
          ├── system_manifest.json
          ├── <institution_short_name>/
          │     └── [export files per adapter]
          └── ...

    Args:
        current_user: Site Admin user dict

    Returns:
        Flask send_file response with system-wide export ZIP
    """
    system_export_dir = None

    try:
        data_type, adapter_id, include_metadata = _sanitize_export_params()
        logger.info(
            f"[EXPORT] Site Admin system-wide export: adapter={adapter_id}, data_type={data_type}"
        )

        institutions = get_all_institutions()
        if not institutions:
            return jsonify({"success": False, "error": "No institutions found"}), 404

        # Setup export directory with UUID for uniqueness
        temp_base = Path(tempfile.gettempdir())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        system_export_dir = temp_base / f"system_export_{timestamp}_{unique_id}"
        system_export_dir.mkdir(parents=True, exist_ok=True)

        export_service = create_export_service()
        adapter = export_service.registry.get_adapter_by_id(adapter_id)
        if not adapter:
            return (
                jsonify(
                    {"success": False, "error": f"Adapter not found: {adapter_id}"}
                ),
                400,
            )

        file_extension = _get_adapter_file_extension(export_service, adapter_id)
        output_format = (
            file_extension.lstrip(".")
            if file_extension.startswith(".")
            else file_extension
        )

        # Export institutions
        institution_results = [
            _export_institution(
                export_service,
                inst,
                system_export_dir,
                adapter_id,
                include_metadata,
                output_format,
                data_type,
                timestamp,
                file_extension,
            )
            for inst in institutions
        ]

        # Create manifest
        system_manifest = _create_system_manifest(
            current_user,
            timestamp,
            adapter_id,
            data_type,
            institutions,
            institution_results,
        )
        manifest_path = system_export_dir / "system_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(system_manifest, f, indent=2)

        # Create ZIP
        system_zip_path = _create_system_export_zip(
            system_export_dir, temp_base, timestamp, unique_id
        )
        shutil.rmtree(system_export_dir)

        logger.info(
            f"[EXPORT] System export complete: {system_manifest['successful_exports']}/{system_manifest['total_institutions']} institutions"
        )

        return send_file(
            str(system_zip_path),
            as_attachment=True,
            download_name=f"system_export_{timestamp}.zip",
            mimetype="application/zip",
        )

    except Exception as e:
        logger.error(f"[EXPORT] System export failed: {str(e)}", exc_info=True)
        if system_export_dir is not None and system_export_dir.exists():
            try:
                shutil.rmtree(system_export_dir)
            except Exception as cleanup_error:
                logger.error(
                    f"[EXPORT] Failed to cleanup temp directory: {str(cleanup_error)}"
                )
        return (
            jsonify({"success": False, "error": f"System export failed: {str(e)}"}),
            500,
        )
