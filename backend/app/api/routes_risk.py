"""Risk and recommendation routes.

Endpoints that expose risk assessments and remediation recommendations. The
ingest endpoints consume Member 5 output; the read endpoints power Member 6's
dashboard.

Two routers are defined here (risks + recommendations) because the provided
file layout keeps both in routes_risk.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app.schemas.risk import RiskAssessment
from app.schemas.recommendation import Recommendation
from app.services.integration_service import (
    ingest_recommendations,
    ingest_risk_assessment,
)
from app.services import scan_service

risks_router = APIRouter(prefix="/risks", tags=["risks"])
recommendations_router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _require_scan(db: Session, scan_id: str) -> models.Scan:
    """Fetch a scan or raise a 404."""
    scan = scan_service.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    return scan


@risks_router.post("/ingest", status_code=204)
def ingest_risk(
    scan_id: str = Query(..., description="Target scan"),
    payload: RiskAssessment = ...,
    db: Session = Depends(get_db),
):
    """Persist a risk assessment produced by Member 5.

    Applies the assessment's risk fields onto the matching crypto asset(s)
    of the scan. A per-asset assessment without a matching asset id is a no-op.
    """
    _require_scan(db, scan_id)
    ingest_risk_assessment(db, scan_id, payload)


@risks_router.post("/run", status_code=200)
def run_risk_engine(
    scan_id: str = Query(..., description="Target scan"),
    db: Session = Depends(get_db),
):
    """Run the deterministic risk engine over a scan's assets (Member 5).

    Convenience trigger that computes risk scores/priorities/recommendations
    for every asset in the scan, persists them via the canonical ingest path,
    and returns the rich M6-facing assessments.
    """
    _require_scan(db, scan_id)
    from app.services.risk_service import assess_scan

    return assess_scan(db, scan_id)


@risks_router.get("")
def list_risks(
    scan_id: str | None = Query(None, description="Filter by scan"),
    db: Session = Depends(get_db),
):
    """List risk assessments for a scan (or all scans)."""
    query = (
        db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.risk_score.is_not(None))
    )
    if scan_id:
        _require_scan(db, scan_id)
        query = query.filter(models.CryptoAssetModel.scan_id == scan_id)

    return [
        {
            "scan_id": a.scan_id,
            "asset_id": a.id,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level,
            "migration_priority": a.migration_priority,
            "mosca_assessment": a.mosca_assessment,
        }
        for a in query.all()
    ]


@risks_router.get("/{scan_id}")
def scan_risks(scan_id: str, db: Session = Depends(get_db)):
    """Risk summary for a single scan (asset-level rows for the dashboard)."""
    _require_scan(db, scan_id)
    assets = (
        db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.scan_id == scan_id)
        .all()
    )
    assessed = [
        {
            "asset_id": a.id,
            "algorithm": a.algorithm,
            "file_path": a.file_path,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level,
            "migration_priority": a.migration_priority,
            "mosca_assessment": a.mosca_assessment,
        }
        for a in assets
        if a.risk_score is not None
    ]
    return {
        "scan_id": scan_id,
        "asset_count": len(assets),
        "assessed_count": len(assessed),
        "assessments": assessed,
    }


@recommendations_router.post("/ingest", status_code=204)
def ingest_recommendations_route(
    scan_id: str = Query(..., description="Target scan"),
    payload: list[Recommendation] = ...,
    db: Session = Depends(get_db),
):
    """Persist recommendations produced by Member 5 for a scan."""
    _require_scan(db, scan_id)
    ingest_recommendations(db, scan_id, payload)


@recommendations_router.get("")
def list_recommendations(
    scan_id: str | None = Query(None, description="Filter by scan"),
    db: Session = Depends(get_db),
):
    """List recommendations, optionally filtered by scan."""
    query = db.query(models.RecommendationModel)
    if scan_id:
        _require_scan(db, scan_id)
        query = query.filter(models.RecommendationModel.scan_id == scan_id)
    return [
        {
            "scan_id": r.scan_id,
            "asset_id": r.asset_id,
            "recommendation": r.recommendation,
            "explanation": r.explanation,
            "suggested_target": r.suggested_target,
            "effort_estimate": r.effort_estimate,
        }
        for r in query.all()
    ]


@recommendations_router.get("/{scan_id}")
def scan_recommendations(scan_id: str, db: Session = Depends(get_db)):
    """Recommendations for a single scan."""
    _require_scan(db, scan_id)
    return [
        {
            "scan_id": scan_id,
            "asset_id": r.asset_id,
            "recommendation": r.recommendation,
            "explanation": r.explanation,
            "suggested_target": r.suggested_target,
            "effort_estimate": r.effort_estimate,
        }
        for r in db.query(models.RecommendationModel)
        .filter(models.RecommendationModel.scan_id == scan_id)
        .all()
    ]