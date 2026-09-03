"""Crypto asset routes.

CRUD over persisted crypto assets (canonical CryptoAsset contract). Includes
the two ingest endpoints used by Member 3 (bulk create assets for a scan) and
the patch endpoint used by Member 5's risk engine to fill risk fields.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.crypto_asset import CryptoAsset, CryptoAssetCreate, CryptoAssetUpdate
from app.services import scan_service

router = APIRouter(prefix="/assets", tags=["assets"])


def _require_asset(db: Session, asset_pk: int) -> models.CryptoAssetModel:
    """Fetch an asset by primary key or raise a 404."""
    asset = db.get(models.CryptoAssetModel, asset_pk)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_pk}' not found")
    return asset


def _to_response(asset: models.CryptoAssetModel) -> dict:
    """Serialize an ORM asset to the canonical CryptoAsset shape."""
    data = {
        "id": asset.id,
        "algorithm": asset.algorithm,
        "operation": asset.operation,
        "key_size": asset.key_size,
        "language": asset.language,
        "library": asset.library,
        "api": asset.api,
        "file_path": asset.file_path,
        "line_number": asset.line_number,
        "evidence": asset.evidence,
        "confidence": asset.confidence,
        "business_criticality": asset.business_criticality,
        "data_lifetime_years": asset.data_lifetime_years,
        "internet_exposure": asset.internet_exposure,
        "migration_complexity": asset.migration_complexity,
        "risk_score": asset.risk_score,
        "risk_level": asset.risk_level,
        "migration_priority": asset.migration_priority,
        "mosca_assessment": asset.mosca_assessment,
        "recommendation": asset.recommendation,
    }
    return {"scan_id": asset.scan_id, **data}


@router.get("", response_model=list[CryptoAsset])
def list_assets(
    scan_id: str | None = Query(None, description="Filter by scan"),
    db: Session = Depends(get_db),
):
    """List crypto assets, optionally filtered by scan."""
    query = db.query(models.CryptoAssetModel)
    if scan_id:
        query = query.filter(models.CryptoAssetModel.scan_id == scan_id)
    return [_to_response(a) for a in query.all()]


@router.get("/{asset_pk}", response_model=CryptoAsset)
def get_asset(asset_pk: int, db: Session = Depends(get_db)):
    """Get a single crypto asset by its database primary key."""
    return _to_response(_require_asset(db, asset_pk))


@router.post("/ingest", response_model=list[CryptoAsset], status_code=201)
def ingest_assets(
    scan_id: str = Query(..., description="Target scan for these assets"),
    payload: list[CryptoAssetCreate] = ...,
    db: Session = Depends(get_db),
):
    """Bulk-ingest crypto assets for a scan (Member 3 integration endpoint).

    `scan_id` is passed as a query parameter so the canonical CryptoAsset
    payload stays clean (it has no relation fields). Persisting replaces any
    previously stored assets for the same scan (idempotent re-scans).
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Empty asset payload")

    # Ensure the target scan actually exists before writing findings.
    if scan_service.get_scan(db, scan_id) is None:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")

    from app.services.integration_service import ingest_crypto_assets

    ingest_crypto_assets(db, scan_id, payload)
    return [
        _to_response(a)
        for a in db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.scan_id == scan_id)
        .all()
    ]


@router.patch("/{asset_pk}", response_model=CryptoAsset)
def update_asset(
    asset_pk: int,
    update: CryptoAssetUpdate,
    db: Session = Depends(get_db),
):
    """Partially update a crypto asset (Member 5 risk fields, M6 edits)."""
    asset = _require_asset(db, asset_pk)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return _to_response(asset)


@router.delete("/{asset_pk}", status_code=204)
def delete_asset(asset_pk: int, db: Session = Depends(get_db)):
    """Delete a single crypto asset."""
    asset = _require_asset(db, asset_pk)
    db.delete(asset)
    db.commit()