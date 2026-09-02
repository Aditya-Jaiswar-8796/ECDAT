"""Risk engine service: bridge between the pure engine and the M1 backend.

Member 5's end-to-end job:
    1. read a scan's persisted CryptoAssets (via SQLAlchemy, Member 1's store);
    2. run them through the deterministic engine (`app.risk_engine`);
    3. push results back through the canonical ingest path so Member 6's
       dashboard sees them:
         - `POST /risks/ingest`      (RiskAssessment per asset)
         - `POST /recommendations/ingest` (Recommendation per asset)
    4. flip the scan lifecycle status to RISK_ASSESSED.

The engine itself stays pure; this module only adapts DB rows <-> AssetInput
and engine results <-> API payloads.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db import models
from app.risk_engine import output, evaluate_scan
from app.risk_engine.config import RiskConfig, default_config
from app.risk_engine.types import AssetInput, BusinessContext
from app.services.integration_service import (
    ingest_recommendations,
    ingest_risk_assessment,
)


def _to_asset_input(asset: models.CryptoAssetModel) -> AssetInput:
    """Map one ORM row to the pure engine input (known fields only)."""
    return AssetInput(
        id=asset.id,
        algorithm=asset.algorithm,
        operation=asset.operation,
        key_size=asset.key_size,
        business_criticality=asset.business_criticality or "MEDIUM",
        data_lifetime_years=asset.data_lifetime_years,
        internet_exposure=asset.internet_exposure or False,
        migration_complexity=asset.migration_complexity or "MEDIUM",
        confidence=asset.confidence or "MEDIUM",
        language=asset.language or "",
        file_path=asset.file_path or "",
    )


def assess_scan(
    db: Session,
    scan_id: str,
    config: Optional[RiskConfig] = None,
    business_contexts: Optional[dict[str, BusinessContext]] = None,
) -> list[dict]:
    """Assess every asset of a scan and persist results through the M1 API path.

    Returns the rich M6-facing views (0-100 details) for direct dashboard use.
    """
    config = config or default_config()
    assets = (
        db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.scan_id == scan_id)
        .all()
    )

    # Run the deterministic pipeline over all rows at once.
    inputs = [_to_asset_input(a) for a in assets]
    assessments = evaluate_scan(inputs, config=config, business_contexts=business_contexts)

    # Persist risk fields via the canonical per-asset ingest function.
    for result in assessments:
        ingest_risk_assessment(db, scan_id, output.to_risk_assessment(result))

    # Also write the recommendation onto the asset's own field (the dashboard's
    # asset views expose it); the dedicated Recommendation table is updated
    # below. Kept in this service — not the generic ingest — because the asset-
    # level recommendation is an M5-specific convenience.
    for result in assessments:
        asset = (
            db.query(models.CryptoAssetModel)
            .filter(
                models.CryptoAssetModel.scan_id == scan_id,
                models.CryptoAssetModel.id == result.asset_id,
            )
            .first()
        )
        if asset is not None:
            asset.recommendation = result.recommendation
    db.commit()

    # Persist recommendations as a batch (idempotent per scan).
    ingest_recommendations(
        db, scan_id, [output.to_recommendation(r) for r in assessments]
    )

    # Flip the scan lifecycle so the dashboard's stage model advances.
    scan = db.get(models.Scan, scan_id)
    if scan is not None:
        scan.status = "RISK_ASSESSED"
        db.commit()

    return [output.to_m6_view(r) for r in assessments]