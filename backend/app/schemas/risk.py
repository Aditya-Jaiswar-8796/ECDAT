"""Risk schema.

Represents the risk assessment output produced by Member 5 for a single
CryptoAsset (or aggregated over the scanned project). The risk fields mirror
(and populate) the matching null fields on the canonical CryptoAsset.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
MigrationPriority = Literal["LOW", "MEDIUM", "HIGH", "URGENT"]


class RiskAssessment(BaseModel):
    """Risk result associated with one crypto asset or the whole scan."""

    # Which asset this risk applies to (optional for scan-level aggregates).
    asset_id: Optional[str] = None

    risk_score: Optional[float] = Field(None, ge=0, le=10)
    risk_level: Optional[RiskLevel] = None
    migration_priority: Optional[MigrationPriority] = None

    # MOSAIC assessment is a free-form qualitative note from Member 5.
    mosca_assessment: Optional[str] = None

    # Optional richer structured breakdown for the dashboard.
    factors: Optional[dict] = None

    model_config = {"from_attributes": True}
