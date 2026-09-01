"""CBOM (Cryptography Bill of Materials) routes.

Consume and expose Member 4's dependency and certificate findings. CBOM is
the machine-readable inventory of crypto-relevant artifacts in a scan.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.certificate import Certificate
from app.schemas.dependency import Dependency
from app.services.integration_service import (
    ingest_certificates,
    ingest_dependencies,
)
from app.services import scan_service

router = APIRouter(prefix="/cbom", tags=["cbom"])


def _require_scan(db: Session, scan_id: str) -> models.Scan:
    """Fetch a scan or raise a 404."""
    scan = scan_service.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    return scan


@router.post("/dependencies/ingest", status_code=204)
def ingest_dependencies_route(
    scan_id: str = Query(..., description="Target scan"),
    payload: list[Dependency] = ...,
    db: Session = Depends(get_db),
):
    """Persist dependency findings from Member 4 for a scan."""
    _require_scan(db, scan_id)
    ingest_dependencies(db, scan_id, payload)


@router.post("/certificates/ingest", status_code=204)
def ingest_certificates_route(
    scan_id: str = Query(..., description="Target scan"),
    payload: list[Certificate] = ...,
    db: Session = Depends(get_db),
):
    """Persist certificate findings from Member 4 for a scan."""
    _require_scan(db, scan_id)
    ingest_certificates(db, scan_id, payload)


@router.get("/{scan_id}/dependencies")
def list_scan_dependencies(scan_id: str, db: Session = Depends(get_db)):
    """Dependencies for a scan (Member 4 output)."""
    _require_scan(db, scan_id)
    return [
        {
            "name": d.name,
            "version": d.version,
            "ecosystem": d.ecosystem,
            "crypto_relevant": d.crypto_relevant,
            "known_vulnerabilities": d.known_vulnerabilities,
            "latest_version": d.latest_version,
        }
        for d in db.query(models.DependencyModel)
        .filter(models.DependencyModel.scan_id == scan_id)
        .all()
    ]


@router.get("/{scan_id}/certificates")
def list_scan_certificates(scan_id: str, db: Session = Depends(get_db)):
    """Certificates for a scan (Member 4 output)."""
    _require_scan(db, scan_id)
    return [
        {
            "subject": c.subject,
            "issuer": c.issuer,
            "serial_number": c.serial_number,
            "fingerprint_sha256": c.fingerprint_sha256,
            "not_valid_before": c.not_valid_before,
            "not_valid_after": c.not_valid_after,
            "signature_algorithm": c.signature_algorithm,
            "key_algorithm": c.key_algorithm,
            "key_size": c.key_size,
            "source_file": c.source_file,
        }
        for c in db.query(models.CertificateModel)
        .filter(models.CertificateModel.scan_id == scan_id)
        .all()
    ]


@router.get("/{scan_id}")
def scan_cbom(scan_id: str, db: Session = Depends(get_db)):
    """Full CBOM for a scan: dependencies + certificates combined."""
    _require_scan(db, scan_id)
    return {
        "scan_id": scan_id,
        "dependencies": [
            {
                "name": d.name,
                "version": d.version,
                "ecosystem": d.ecosystem,
                "crypto_relevant": d.crypto_relevant,
            }
            for d in db.query(models.DependencyModel)
            .filter(models.DependencyModel.scan_id == scan_id)
            .all()
        ],
        "certificates": [
            {
                "subject": c.subject,
                "issuer": c.issuer,
                "signature_algorithm": c.signature_algorithm,
                "key_size": c.key_size,
            }
            for c in db.query(models.CertificateModel)
            .filter(models.CertificateModel.scan_id == scan_id)
            .all()
        ],
    }