"""Pure datastructures used by the risk engine.

These mirror the fields of the canonical CryptoAsset contract but keep the engine
decoupled from FastAPI/Pydantic so it can run standalone and be unit-tested
without a web stack. The adapter layer (`output.py`) converts these back into
the team's RiskAssessment / CryptoAsset Pydantic schemas for Member 1 ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

# Canonical risk level vocabulary (matches schema literals).
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Canonical migration priority bucket (matches schema literals). The engine
# derives a P1..P4 priority and maps it onto this envelope vocabulary.
MigrationPriority = Literal["URGENT", "HIGH", "MEDIUM", "LOW"]

# Canonical business / migration adjectives from the CryptoAsset contract.
Criticality = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Complexity = Literal["LOW", "MEDIUM", "HIGH"]

# Broad primitive families used to choose the vulnerability model.
AlgorithmCategory = Literal["asymmetric", "symmetric", "hash", "mac", "unknown"]


@dataclass(frozen=True)
class AssetInput:
    """The canonical fields the risk engine consumes from a CryptoAsset.

    Unknown/missing values are represented as None so the engine can exercise
    its explicit missing-value policy instead of guessing.
    """

    id: str
    algorithm: str
    operation: str = "encryption"
    key_size: Optional[int] = None
    business_criticality: Criticality = "MEDIUM"
    data_lifetime_years: Optional[int] = None
    internet_exposure: bool = False
    migration_complexity: Complexity = "MEDIUM"
    confidence: str = "MEDIUM"
    language: str = ""
    file_path: str = ""


@dataclass(frozen=True)
class BusinessContext:
    """Editable, user-supplied business context that overrides scanner defaults.

    Keeping this separate from the scanner output lets an analyst correct or
    enrich the business impact of an asset without re-running the scan.
    All fields are optional: None means "use the scanner value / conservative
    default".
    """

    business_criticality: Optional[Criticality] = None
    data_lifetime_years: Optional[int] = None
    internet_exposure: Optional[bool] = None
    migration_complexity: Optional[Complexity] = None

    def effective(self, asset: AssetInput) -> AssetInput:
        """Return an AssetInput with business-context overrides applied.

        Business context always wins over the scanner-supplied value when both
        are present; otherwise the input value is kept as-is.
        """
        return AssetInput(
            id=asset.id,
            algorithm=asset.algorithm,
            operation=asset.operation,
            key_size=asset.key_size,
            business_criticality=(
                self.business_criticality
                if self.business_criticality is not None
                else asset.business_criticality
            ),
            data_lifetime_years=(
                self.data_lifetime_years
                if self.data_lifetime_years is not None
                else asset.data_lifetime_years
            ),
            internet_exposure=(
                self.internet_exposure
                if self.internet_exposure is not None
                else asset.internet_exposure
            ),
            migration_complexity=(
                self.migration_complexity
                if self.migration_complexity is not None
                else asset.migration_complexity
            ),
            confidence=asset.confidence,
            language=asset.language,
            file_path=asset.file_path,
        )


@dataclass(frozen=True)
class AlgorithmConcern:
    """Result of profiling a detected algorithm.

    `vulnerability_score` is the algorithm-contribution to the final risk score
    (0-100). `susceptibility` is a 0..1 factor used by the Mosca boost.
    """

    algorithm: str
    category: AlgorithmCategory
    known: bool
    vulnerability_score: float
    susceptibility: float
    migration_risk_weight: float = 0.0
    reason: str = ""
    # Suggested PQ-ready replacement (candidate) chosen from the editable mapping.
    suggested_target: Optional[str] = None
    # Whether the algorithm is already PQ-resistant (e.g. ML-KEM, AES-256 in use).
    is_post_quantum: bool = False


@dataclass(frozen=True)
class RiskFactorBreakdown:
    """Per-component scores so the result is fully auditable."""

    algorithm_score: float
    lifetime_score: float
    criticality_score: float
    exposure_score: float
    complexity_score: float
    mosca_boost: float

    def as_dict(self) -> dict:
        """Serialize to a flat dict for API/explanation output."""
        return {
            "algorithm": round(self.algorithm_score, 2),
            "data_lifetime": round(self.lifetime_score, 2),
            "business_criticality": round(self.criticality_score, 2),
            "internet_exposure": round(self.exposure_score, 2),
            "migration_complexity": round(self.complexity_score, 2),
            "mosca_boost": round(self.mosca_boost, 2),
        }


@dataclass(frozen=True)
class MoscaAssessment:
    """Structured Mosca-style reasoning.

    Mosca's framing: an asset is at post-quantum risk when it must protect
    secret data for `X` years and it takes `Y` years to migrate, while a
    functional quantum adversary is expected to appear within `Z` years
    (X + Y > Z => urgent). This version uses a configurable planning horizon
    for Z rather than an invented calendar date.
    """

    data_lifetime: Optional[int]
    planning_horizon_years: int
    migration_years: int
    harvest_now_risk: bool
    risk_statement: str
    diagnostic: str


@dataclass(frozen=True)
class AssetAssessment:
    """The complete deterministic output for one asset."""

    asset_id: str
    score_100: float
    score_10: float
    risk_level: RiskLevel
    migration_priority: MigrationPriority
    priority_tier: int
    mosca: MoscaAssessment
    breakdown: RiskFactorBreakdown
    recommendation: str
    explanation: str
    suggested_target: Optional[str]
    effort_estimate: Optional[str]
    trade_offs: list = field(default_factory=list)
    reason: str = ""
    algorithm_known: bool = True
