"""Scan lifecycle + upload routes.

Covers creating scans, uploading project bundles (validated, traversal-safe),
listing scans and querying aggregate counts for a scan. The actual source
parsing is delegated to Member 3 via integration_service.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.scan import Scan, ScanCreate
from app.services import scan_service
from app.services import pipeline_service

router = APIRouter(prefix="/scans", tags=["scans"])


def _require_scan(db: Session, scan_id: str) -> models.Scan:
    """Fetch a scan or raise a 404 with an explicit message."""
    scan = scan_service.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    return scan


@router.post("", response_model=Scan, status_code=201)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db)):
    """Create a new scan in RECEIVED state."""
    return scan_service.create_scan(db, payload)


@router.post("/{scan_id}/upload", response_model=Scan)
def upload_bundle(
    scan_id: str, upload: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Upload a project archive for a scan.

    The archive is validated and stored in the scan's staging directory for
    Member 3 to parse. No code from the upload is ever executed.
    """
    scan = _require_scan(db, scan_id)
    stored = scan_service.persist_upload(scan, upload)

    # Confirm the archive is a readable ZIP; extraction itself is left to M3.
    try:
        with zipfile.ZipFile(stored) as zf:
            bad = zf.testzip()
            if bad:
                scan_service.set_error(
                    db, scan, f"Corrupt archive member: {bad}"
                )
                raise HTTPException(
                    status_code=400, detail=f"Corrupt archive member: {bad}"
                )
            # Reject path-traversal members up front (defense in depth, in
            # addition to scan_service.safe_extract used later by M3).
            resolver = Path(stored).resolve().parent
            for member in zf.infolist():
                target = (resolver / member.filename).resolve()
                if not target.is_relative_to(resolver):
                    scan_service.set_error(
                        db, scan, f"Archive contains illegal path: {member.filename}"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Archive contains illegal path: {member.filename}",
                    )
                # Reject symlink members (mode bits: 0o120000 == symlink).
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    scan_service.set_error(db, scan, "Symlinks not allowed")
                    raise HTTPException(
                        status_code=400, detail="Symlinks are not allowed in uploads"
                    )
    except zipfile.BadZipFile as exc:
        scan_service.set_error(db, scan, "Uploaded file is not a valid ZIP")
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a valid ZIP"
        ) from exc

    scan_service.set_status(db, scan, "SCANNING")

    # Kick off the async analysis pipeline (extract + scan + risk) in a
    # background thread so the upload responds immediately. The frontend
    # watches status via its existing polling.
    pipeline_service._start_pipeline(scan_id)
    return scan


@router.get("", response_model=list[Scan])
def list_scans(db: Session = Depends(get_db)):
    """List all scans newest first."""
    return scan_service.list_scans(db)


@router.get("/{scan_id}", response_model=Scan)
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    """Get a single scan by id."""
    return _require_scan(db, scan_id)


@router.delete("", status_code=200)
def clear_all_scans(db: Session = Depends(get_db)):
    """Delete every scan, its findings and staged uploads.

    Returns the count of removed scans. Used by the dashboard's
    'Clear all scans' action.
    """
    removed = scan_service.clear_scans(db)
    return {"deleted": removed}


@router.get("/{scan_id}/summary")
def scan_summary(scan_id: str, db: Session = Depends(get_db)):
    """Aggregate counts for the scan's findings (used by the dashboard)."""
    _require_scan(db, scan_id)

    asset_count = (
        db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.scan_id == scan_id)
        .count()
    )
    dependency_count = (
        db.query(models.DependencyModel)
        .filter(models.DependencyModel.scan_id == scan_id)
        .count()
    )
    certificate_count = (
        db.query(models.CertificateModel)
        .filter(models.CertificateModel.scan_id == scan_id)
        .count()
    )
    recommendation_count = (
        db.query(models.RecommendationModel)
        .filter(models.RecommendationModel.scan_id == scan_id)
        .count()
    )
    return {
        "asset_count": asset_count,
        "dependency_count": dependency_count,
        "certificate_count": certificate_count,
        "recommendation_count": recommendation_count,
    }