"""Canonical CryptoAsset schema.

This is the SINGLE integration contract used across the entire ECDAT project.
Members 3, 4, 5 and 6 all exchange data through this schema. It must NOT be
duplicated or redefined anywhere else. If the shape changes, update it here
and propagate through the API contract (docs/api_contract.md).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# Literal value sets kept in one place so validation stays consistent.
ConfidenceLevel = Literal["LOW", "MEDIUM", "HIGH"]
CriticalityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
MigrationComplexity = Literal["LOW", "MEDIUM", "HIGH"]


class CryptoAssetBase(BaseModel):
    """Source-scan finding describing a single cryptographic primitive."""

    # Stable identifier produced by the source scanner (Member 3).
    id: str
    algorithm: str
    operation: str
    key_size: Optional[int] = None
    language: str
    library: Optional[str] = None
    api: Optional[str] = None

    # Location evidence within the scanned source tree.
    file_path: str
    line_number: Optional[int] = None
    evidence: Optional[str] = None

    confidence: ConfidenceLevel = "MEDIUM"
    business_criticality: CriticalityLevel = "MEDIUM"
    data_lifetime_years: Optional[int] = None
    internet_exposure: bool = False
    migration_complexity: MigrationComplexity = "MEDIUM"

    # Fields populated later by the risk engine (Member 5). Null until then.
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    migration_priority: Optional[str] = None
    mosca_assessment: Optional[str] = None
    recommendation: Optional[str] = None


class CryptoAssetCreate(CryptoAssetBase):
    """Payload used to persist a new crypto asset into the store."""

    pass


class CryptoAssetUpdate(BaseModel):
    """Partial update, primarily used by the risk engine (Member 5) to fill
    in the risk fields, and by the dashboard (Member 6) to edit metadata."""

    algorithm: Optional[str] = None
    operation: Optional[str] = None
    key_size: Optional[int] = None
    language: Optional[str] = None
    library: Optional[str] = None
    api: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: Optional[str] = None
    confidence: Optional[ConfidenceLevel] = None
    business_criticality: Optional[CriticalityLevel] = None
    data_lifetime_years: Optional[int] = None
    internet_exposure: Optional[bool] = None
    migration_complexity: Optional[MigrationComplexity] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    migration_priority: Optional[str] = None
    mosca_assessment: Optional[str] = None
    recommendation: Optional[str] = None


class CryptoAsset(CryptoAssetBase):
    """Full asset record as returned by the API (serialized to a response).

    The `id` in the AutoModel contract is the asset id, so we expose it at
    the top level of the response (aliased from the internal DB primary key
    name if needed).
    """

    # DB primary key carries the same semantic as the assetidentifier.
    pk: Optional[int] = Field(default=None, exclude=True)

    model_config = {"from_attributes": True}
