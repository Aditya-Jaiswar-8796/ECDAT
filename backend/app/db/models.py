"""SQLAlchemy ORM models for the ECDAT backend.

Models mirror the canonical schemas. The `CryptoAsset` model is the persisted
form of the canonical CryptoAsset schema and is the integration contract with
the rest of the pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.db.database import Base


def _utcnow() -> datetime:
    """Return the current UTC timestamp for default column values."""
    return datetime.now(timezone.utc)


class Scan(Base):
    """A submitted project bundle and its lifecycle status."""

    __tablename__ = "scans"

    scan_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    project_name: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)

    status: Mapped[str] = mapped_column(String, default="RECEIVED")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    # Relationships to the findings collected for this scan.
    assets = relationship(
        "CryptoAssetModel", back_populates="scan", cascade="all, delete-orphan"
    )
    dependencies = relationship("DependencyModel", back_populates="scan",
                                cascade="all, delete-orphan")
    certificates = relationship("CertificateModel", back_populates="scan",
                                cascade="all, delete-orphan")
    recommendations = relationship(
        "RecommendationModel", back_populates="scan",
        cascade="all, delete-orphan"
    )

    @hybrid_property
    def asset_count(self) -> int:
        return len(self.assets) if self.assets else 0

    @hybrid_property
    def dependency_count(self) -> int:
        return len(self.dependencies) if self.dependencies else 0

    @hybrid_property
    def certificate_count(self) -> int:
        return len(self.certificates) if self.certificates else 0


class CryptoAssetModel(Base):
    """Persisted cryptographic primitive finding (canonical CryptoAsset)."""

    __tablename__ = "crypto_assets"

    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String, nullable=False)

    # FK to the scan that produced this asset.
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False
    )

    algorithm: Mapped[str] = mapped_column(String, nullable=False)
    operation: Mapped[str] = mapped_column(String, default="")
    key_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String, default="")
    library: Mapped[str | None] = mapped_column(String, nullable=True)
    api: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str] = mapped_column(String, default="")
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    confidence: Mapped[str] = mapped_column(String, default="MEDIUM")
    business_criticality: Mapped[str] = mapped_column(String, default="MEDIUM")
    data_lifetime_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    internet_exposure: Mapped[bool] = mapped_column(Boolean, default=False)
    migration_complexity: Mapped[str] = mapped_column(String, default="MEDIUM")

    # Risk fields populated later by Member 5 (null until then).
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String, nullable=True)
    migration_priority: Mapped[str | None] = mapped_column(String, nullable=True)
    mosca_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    scan = relationship("Scan", back_populates="assets")


class DependencyModel(Base):
    """A dependency detected in a scan (Member 4 output)."""

    __tablename__ = "dependencies"

    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    ecosystem: Mapped[str | None] = mapped_column(String, nullable=True)
    crypto_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    known_vulnerabilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_version: Mapped[str | None] = mapped_column(String, nullable=True)

    scan = relationship("Scan", back_populates="dependencies")


class CertificateModel(Base):
    """A certificate discovered in a scan (Member 4 output)."""

    __tablename__ = "certificates"

    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False
    )
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    issuer: Mapped[str | None] = mapped_column(String, nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String, nullable=True)
    fingerprint_sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    not_valid_before: Mapped[str | None] = mapped_column(String, nullable=True)
    not_valid_after: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_algorithm: Mapped[str | None] = mapped_column(String, nullable=True)
    key_algorithm: Mapped[str | None] = mapped_column(String, nullable=True)
    key_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String, nullable=True)

    scan = relationship("Scan", back_populates="certificates")


class RecommendationModel(Base):
    """A recommendation produced by Member 5."""

    __tablename__ = "recommendations"

    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_target: Mapped[str | None] = mapped_column(String, nullable=True)
    effort_estimate: Mapped[str | None] = mapped_column(String, nullable=True)

    scan = relationship("Scan", back_populates="recommendations")
