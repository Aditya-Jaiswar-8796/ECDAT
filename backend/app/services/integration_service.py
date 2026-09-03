"""Integration service.

Member 1 owns persistence and stable API exposure. This service defines the
interfaces/adapters used to ingest normalized findings from the other members
and to hand a completed scan over to the risk engine. The concrete
implementations are stubs that members 3/4/5 will wire up; Member 1 only
defines the contract (the method signatures and the canonical payload shapes).

Integration flow:
    M3 + M4 --findings--> M1 (ingest) --> M5 (risk) --> M1 API exposure --> M6
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.schemas.certificate import Certificate
from app.schemas.crypto_asset import CryptoAssetCreate
from app.schemas.dependency import Dependency
from app.schemas.risk import RiskAssessment
from app.schemas.recommendation import Recommendation


def ingest_crypto_assets(
    db: Session, scan_id: str, assets: list[CryptoAssetCreate]
) -> int:
    """Persist normalized source-scan findings from Member 3.

    Replaces any existing assets for the scan so re-runs are idempotent.
    Returns the number of assets persisted.
    """
    # Remove previous findings so a re-scan does not accumulate duplicates.
    db.query(models.CryptoAssetModel).filter(
        models.CryptoAssetModel.scan_id == scan_id
    ).delete()

    for a in assets:
        db.add(models.CryptoAssetModel(scan_id=scan_id, **a.model_dump()))
    db.commit()
    return len(assets)


def ingest_dependencies(
    db: Session, scan_id: str, deps: list[Dependency]
) -> int:
    """Persist dependency findings from Member 4 (idempotent for re-runs)."""
    db.query(models.DependencyModel).filter(
        models.DependencyModel.scan_id == scan_id
    ).delete()

    for d in deps:
        db.add(models.DependencyModel(scan_id=scan_id, **d.model_dump()))
    db.commit()
    return len(deps)


def ingest_certificates(
    db: Session, scan_id: str, certs: list[Certificate]
) -> int:
    """Persist certificate findings from Member 4 (idempotent for re-runs)."""
    db.query(models.CertificateModel).filter(
        models.CertificateModel.scan_id == scan_id
    ).delete()

    for c in certs:
        db.add(models.CertificateModel(scan_id=scan_id, **c.model_dump()))
    db.commit()
    return len(certs)


def ingest_risk_assessment(
    db: Session, scan_id: str, assessment: RiskAssessment
) -> None:
    """Apply per-asset risk fields returned by Member 5 back onto the scan's
    crypto assets.

    The risk engine returns one RiskAssessment (for a single asset) or a
    list. For simplicity, per-asset assessments are applied via the asset's
    `id`; scan-level assessments update all assets of the scan.
    """
    assets = (
        db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.scan_id == scan_id)
        .all()
    )

    for asset in assets:
        if assessment.asset_id is not None and asset.id != assessment.asset_id:
            # Skip assets unrelated to this per-asset assessment.
            continue
        asset.risk_score = assessment.risk_score
        asset.risk_level = assessment.risk_level
        asset.migration_priority = assessment.migration_priority
        asset.mosca_assessment = assessment.mosca_assessment
    db.commit()


def ingest_recommendations(
    db: Session, scan_id: str, recommendations: list[Recommendation]
) -> int:
    """Persist recommendations produced by Member 5."""

    db.query(models.RecommendationModel).filter(
        models.RecommendationModel.scan_id == scan_id
    ).delete()

    for r in recommendations:
        payload = r.model_dump()
        # scan_id is owned by the DB row, not the schema value — drop it from
        # the dump so we don't pass it twice when setting it explicitly above.
        payload.pop("scan_id", None)
        db.add(models.RecommendationModel(scan_id=scan_id, **payload))
    db.commit()
    return len(recommendations)
