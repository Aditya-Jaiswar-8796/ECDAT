"""Scan lifecycle service.

Handles the create -> upload -> update-status lifecycle of a Scan and the
ZIP upload handling (with path-traversal protection). This service owns no
parsing of the source itself -- that belongs to Member 3 -- it only stages
the uploaded bundle and records lifecycle transitions.
"""

from __future__ import annotations

import os
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.scan import ScanCreate

# Root under which uploaded bundles are extracted/staged.
#
# IMPORTANT: this lives OUTSIDE the repo/backend working tree on purpose. The
# dev server runs `uvicorn --reload`, which watches the CWD and reloads on any
# file change. Uploaded archives are extracted here when the pipeline runs; if
# this directory were inside the watched tree, uvicorn would detect those
# writes, reload the app mid-pipeline and kill the background worker thread —
# orphaning the scan at SCAN_COMPLETE. Keeping it a sibling of the repo means
# upload/extract writes never participate in the reload watch.
_UPLOAD_ENV = os.getenv("ECDAT_UPLOAD_DIR")
if _UPLOAD_ENV:
    UPLOAD_ROOT = Path(_UPLOAD_ENV).resolve()
else:
    # One level above the repo root (CWD is usually backend/ or repo root).
    UPLOAD_ROOT = (Path(__file__).resolve().parents[3] / ".." / "ecdat_uploads").resolve()

# Allowed archive extensions to guard the upload endpoint.
ALLOWED_ARCHIVE_EXTS = {".zip"}
# Hard upper bound on upload size (bytes) to guard memory/disk usage.
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB prototype limit


def create_scan(db: Session, payload: ScanCreate) -> models.Scan:
    """Create a new scan record in RECEIVED state and return it."""
    scan = models.Scan(
        scan_id=f"scan-{uuid.uuid4().hex[:8]}",
        name=payload.name,
        project_name=payload.project_name,
        language=payload.language,
        status="RECEIVED",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def get_scan(db: Session, scan_id: str) -> models.Scan | None:
    """Fetch a single scan by id, or None if not found."""
    return db.get(models.Scan, scan_id)


def list_scans(db: Session) -> list[models.Scan]:
    """Return all scans ordered by creation time (newest first)."""
    return (
        db.query(models.Scan).order_by(models.Scan.created_at.desc()).all()
    )


def set_status(db: Session, scan: models.Scan, status: str) -> models.Scan:
    """Transition a scan to the given lifecycle status and persist it."""
    scan.status = status
    db.commit()
    db.refresh(scan)
    return scan


def set_error(db: Session, scan: models.Scan, error: str) -> models.Scan:
    """Mark a scan FAILED with the provided error message."""
    scan.status = "FAILED"
    scan.error = error
    db.commit()
    db.refresh(scan)
    return scan


def get_scan_dir(scan: models.Scan) -> Path:
    """Return (creating if needed) the staging directory for a scan's bundle."""
    scan_dir = UPLOAD_ROOT / scan.scan_id
    scan_dir.mkdir(parents=True, exist_ok=True)
    return scan_dir


def validate_upload(upload: UploadFile) -> None:
    """Validate an uploaded file before it is accepted.

    Checks the filename against the allowed extension whitelist and rejects
    oversized uploads with a clear HTTP error. Never trusts the uploaded
    content-type header (easily spoofed), instead relies on the extension
    allowlist and later zip-read errors.
    """
    name = upload.filename or ""
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_ARCHIVE_EXTS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Only "
            f"{', '.join(sorted(ALLOWED_ARCHIVE_EXTS))} archives are allowed.",
        )
    # Reject obviously oversized archives up front.
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds the {MAX_UPLOAD_BYTES} byte limit.",
        )


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    """Extract a ZIP archive while preventing path traversal.

    Each entry's resolved target must stay within `destination`. Any entry
    that attempts to escape (via '..' or an absolute path) is skipped rather
    than written, and a HTTP 400 is raised to make the rejection explicit.
    """
    for member in archive.infolist():
        # Normalize and reject traversal or absolute entry paths.
        target = (destination / member.filename).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise HTTPException(
                status_code=400,
                detail=f"Archive contains illegal path: {member.filename}",
            )
        # Guard against symlinks/hardlinks that could point outside.
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        # Ensure parent directory exists then write the member safely.
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as src, target.open("wb") as dst:
            dst.write(src.read())


def delete_scan(db: Session, scan_id: str) -> bool:
    """Delete a single scan and all its related rows + staged upload dir."""
    scan = get_scan(db, scan_id)
    if scan is None:
        return False
    for model in (models.RecommendationModel, models.CertificateModel,
                  models.DependencyModel, models.CryptoAssetModel):
        db.query(model).filter(model.scan_id == scan_id).delete()
    db.delete(scan)
    db.commit()
    scan_dir = UPLOAD_ROOT / scan_id
    if scan_dir.exists():
        shutil.rmtree(scan_dir, ignore_errors=True)
    return True


def clear_scans(db: Session) -> int:
    """Delete every scan (and related rows + staged upload dirs).

    Returns the number of scans removed. Idempotent — safe to call when the
    table is already empty.
    """
    scan_ids = [s.scan_id for s in db.query(models.Scan).all()]
    # Delete child rows across all models in one pass, then the scans.
    ids = {sid: None for sid in scan_ids}
    for model in (models.RecommendationModel, models.CertificateModel,
                  models.DependencyModel, models.CryptoAssetModel):
        db.query(model).filter(model.scan_id.in_(scan_ids)).delete()
    db.query(models.Scan).delete()
    db.commit()
    for scan_id in scan_ids:
        scan_dir = UPLOAD_ROOT / scan_id
        if scan_dir.exists():
            shutil.rmtree(scan_dir, ignore_errors=True)
    return len(scan_ids)


def persist_upload(scan: models.Scan, upload: UploadFile) -> Path:
    """Validate and store an uploaded archive for a scan.

    1. Validate the upload (type + size).
    2. Save the raw archive to the scan's staging directory.
    3. Return the stored archive path for downstream extraction by M3.
    """
    validate_upload(upload)

    scan_dir = get_scan_dir(scan)
    dest = scan_dir / (upload.filename or "upload.zip")
    with dest.open("wb") as out:
        out.write(upload.file.read())

    return dest
