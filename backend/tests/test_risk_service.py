"""Integration tests: risk engine service against a real (in-memory) DB.

Exercises the M3 -> M5 -> M1 path end to end:
    ingest assets -> risk_service.assess_scan -> persisted risk fields
    + recommendations + scan status, then re-reads for M6.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.database import Base
from app.schemas.crypto_asset import CryptoAssetCreate
from app.risk_engine.config import default_config
from app.services import risk_service, scan_service
from app.schemas.scan import ScanCreate


@pytest.fixture()
def db():
    """A fresh in-memory SQLite session with the full schema."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _seed_scan_with_assets(db, assets: list[CryptoAssetCreate]) -> str:
    """Create a scan and ingest assets via the canonical M3 path, returning scan_id."""
    from app.services.integration_service import ingest_crypto_assets

    scan = scan_service.create_scan(db, ScanCreate(name="demo", language="java"))
    ingest_crypto_assets(db, scan.scan_id, assets)
    return scan.scan_id


def test_assess_scan_persists_risk_and_recommendations(db):
    """End-to-end: risks + recommendations land on the DB readable by M6."""
    asset = CryptoAssetCreate(
        id="asset-001",
        algorithm="RSA",
        operation="keyexchange",
        key_size=2048,
        language="java",
        file_path="src/PaymentService.java",
        business_criticality="CRITICAL",
        data_lifetime_years=25,
        internet_exposure=True,
        migration_complexity="HIGH",
    )
    scan_id = _seed_scan_with_assets(db, [asset])

    views = risk_service.assess_scan(db, scan_id, config=default_config())

    # Engine produced exactly one assessment.
    assert len(views) == 1
    assert views[0]["asset_id"] == "asset-001"

    # Risk fields are now persisted on the asset (what M6 /assets returns).
    stored = (
        db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.scan_id == scan_id)
        .one()
    )
    assert stored.risk_score is not None
    assert 0 <= stored.risk_score <= 10
    assert stored.risk_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert stored.migration_priority in {"LOW", "MEDIUM", "HIGH", "URGENT"}
    assert stored.mosca_assessment  # Mosca text is populated.
    assert stored.recommendation

    # Recommendations are persisted separately (M6 /recommendations).
    recs = (
        db.query(models.RecommendationModel)
        .filter(models.RecommendationModel.scan_id == scan_id)
        .all()
    )
    assert len(recs) == 1
    assert recs[0].suggested_target  # candidate target present.

    # Scan lifecycle advanced for the dashboard stage model.
    assert db.get(models.Scan, scan_id).status == "RISK_ASSESSED"


def test_assess_scan_handles_mixed_green_and_red(db):
    """PQ-safe and at-risk assets coexist without contaminating each other."""
    assets = [
        CryptoAssetCreate(
            id="safe",
            algorithm="ML-KEM-768",
            operation="keyexchange",
            language="go",
            file_path="tls.go",
            business_criticality="HIGH",
            data_lifetime_years=50,
            internet_exposure=True,
        ),
        CryptoAssetCreate(
            id="risky",
            algorithm="RSA",
            operation="encryption",
            key_size=1024,
            language="python",
            file_path="crypto.py",
            business_criticality="HIGH",
            data_lifetime_years=25,
            internet_exposure=True,
            migration_complexity="MEDIUM",
        ),
    ]
    scan_id = _seed_scan_with_assets(db, assets)

    views = risk_service.assess_scan(db, scan_id, config=default_config())
    by_id = {v["asset_id"]: v for v in views}

    assert by_id["safe"]["risk_level"] == "LOW"
    assert by_id["risky"]["risk_level"] in {"HIGH", "CRITICAL"}
    assert by_id["safe"]["risk_score"] < by_id["risky"]["risk_score"]


def test_assess_scan_is_reproducible_and_idempotent(db):
    """Re-running assessment overwrites, never duplicates, results."""
    asset = CryptoAssetCreate(
        id="a1",
        algorithm="ECDSA",
        operation="signing",
        key_size=256,
        language="java",
        file_path="Sign.java",
    )
    scan_id = _seed_scan_with_assets(db, [asset])

    risk_service.assess_scan(db, scan_id, config=default_config())
    first = risk_service.assess_scan(db, scan_id, config=default_config())

    assert len(first) == 1
    stored = (
        db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.scan_id == scan_id)
        .count()
    )
    recs = (
        db.query(models.RecommendationModel)
        .filter(models.RecommendationModel.scan_id == scan_id)
        .count()
    )
    assert stored == 1
    assert recs == 1  # not 2: re-assess replaced the recommendation set.


def test_scan_with_no_assets_is_passthrough(db):
    """A scan with zero assets assesses cleanly to an empty list."""
    scan = scan_service.create_scan(db, ScanCreate(name="empty"))
    views = risk_service.assess_scan(db, scan.scan_id, config=default_config())
    assert views == []