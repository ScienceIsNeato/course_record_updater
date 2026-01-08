"""Institution service for managing institution data and branding.

Provides:
- CRUD operations for institution records
- Logo upload/storage/deletion
- Branding context for templates (logo, name, website)
"""

from __future__ import annotations

import logging
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from src.database import database_service as db
from src.utils.constants import (
    DEFAULT_INSTITUTION_LOGO_STATIC_PATH,
    DEFAULT_INSTITUTION_NAME,
    DEFAULT_INSTITUTION_SHORT_NAME,
    INSTITUTION_NOT_FOUND_MSG,
)

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from werkzeug.datastructures import FileStorage


@dataclass
class InstitutionBranding:
    """Represents branding information for template rendering."""

    institution_id: Optional[str]
    name: str
    short_name: str
    website_url: Optional[str]
    logo_path: str
    has_custom_logo: bool


class InstitutionServiceError(Exception):
    """Base exception for institution service operations."""


class LogoValidationError(InstitutionServiceError):
    """Raised when logo uploads fail validation."""


class InstitutionService:
    """High-level institution operations and branding helpers."""

    ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/svg+xml"}
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

    def __init__(self, upload_root: Optional[Path] = None):
        self.upload_root = upload_root or Path("static/uploads/institutions")
        self.upload_root.mkdir(parents=True, exist_ok=True)

    def get_institution(self, institution_id: str) -> Dict:
        institution = db.get_institution_by_id(institution_id)
        if not institution:
            raise InstitutionServiceError(INSTITUTION_NOT_FOUND_MSG)
        return institution

    def save_logo(
        self, institution_id: str, file: "FileStorage", *, allow_empty: bool = False
    ) -> Optional[str]:
        if file.filename == "" or (
            file.content_length is not None and file.content_length == 0
        ):
            if allow_empty:
                return None
            raise LogoValidationError("No file provided")

        if file.mimetype not in self.ALLOWED_MIME_TYPES:
            raise LogoValidationError("Invalid file type. Allowed: PNG, JPEG, SVG")

        if file.content_length and file.content_length > self.MAX_FILE_SIZE_BYTES:
            raise LogoValidationError("Logo file is too large (max 5 MB)")

        extension = (
            mimetypes.guess_extension(file.mimetype) or Path(file.filename).suffix
        )
        safe_extension = extension.lower()
        if safe_extension not in {".png", ".jpg", ".jpeg", ".svg"}:
            raise LogoValidationError("Unsupported logo file extension")

        target_dir = self.upload_root / institution_id
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / f"logo{safe_extension}"
        file.save(target_path)

        relative_path = os.path.relpath(target_path, Path("static"))
        return relative_path.replace(os.path.sep, "/")

    def delete_logo(self, institution_id: str) -> None:
        target_dir = self.upload_root / institution_id
        if not target_dir.exists():
            return

        for file in target_dir.iterdir():
            if file.is_file():
                try:
                    file.unlink()
                except OSError:
                    LOGGER.warning("Failed to delete logo file %s", file)

    def update_institution_branding(
        self,
        institution_id: str,
        *,
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        website_url: Optional[str] = None,
        logo: Optional["FileStorage"] = None,
        remove_logo: bool = False,
    ) -> Dict:
        institution = self.get_institution(institution_id)

        updates: Dict[str, Optional[str]] = {}
        if name is not None:
            updates["name"] = name.strip()
        if short_name is not None:
            updates["short_name"] = short_name.strip().upper()
        if website_url is not None:
            updates["website_url"] = website_url.strip() or None

        existing_logo = institution.get("logo_path")

        if remove_logo and existing_logo:
            updates["logo_path"] = None
            self.delete_logo(institution_id)

        if logo:
            if existing_logo:
                self.delete_logo(institution_id)
            new_path = self.save_logo(institution_id, logo)
            updates["logo_path"] = new_path
            LOGGER.info("Updated logo for institution %s", institution_id)

        if updates:
            db.update_institution(institution_id, updates)

        return db.get_institution_by_id(institution_id)

    def build_branding(self, institution_id: Optional[str]) -> InstitutionBranding:
        if not institution_id:
            return InstitutionBranding(
                institution_id=None,
                name=DEFAULT_INSTITUTION_NAME,
                short_name=DEFAULT_INSTITUTION_SHORT_NAME,
                website_url=None,
                logo_path=DEFAULT_INSTITUTION_LOGO_STATIC_PATH,
                has_custom_logo=False,
            )

        institution = db.get_institution_by_id(institution_id)
        if not institution:
            LOGGER.warning(
                "Institution %s not found; using default branding", institution_id
            )
            return InstitutionBranding(
                institution_id=None,
                name=DEFAULT_INSTITUTION_NAME,
                short_name=DEFAULT_INSTITUTION_SHORT_NAME,
                website_url=None,
                logo_path=DEFAULT_INSTITUTION_LOGO_STATIC_PATH,
                has_custom_logo=False,
            )

        logo_path = institution.get("logo_path")
        has_custom_logo = bool(logo_path)

        return InstitutionBranding(
            institution_id=institution.get("institution_id") or institution.get("id"),
            name=institution.get("name") or DEFAULT_INSTITUTION_NAME,
            short_name=institution.get("short_name") or DEFAULT_INSTITUTION_SHORT_NAME,
            website_url=institution.get("website_url"),
            logo_path=logo_path or DEFAULT_INSTITUTION_LOGO_STATIC_PATH,
            has_custom_logo=has_custom_logo,
        )
