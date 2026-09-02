"""EC DAT Risk Engine (Member 5).

Deterministic, transparent post-quantum readiness scoring over the canonical
CryptoAsset findings. No LLM/ML decides the authoritative risk score — every
component is computed from explicit, configurable factors and weights, and each
assessment carries a machine-readable explanation of how the score was derived.

Pipeline:
    CryptoAsset
      -> algorithm concern + data lifetime + business criticality
         + internet exposure + migration complexity
      -> deterministic 0-100 score
      -> risk_level (LOW/MEDIUM/HIGH/CRITICAL)
      -> migration_priority (P1/P2/P3/P4)
      -> Mosca-style assessment
      -> recommendation (candidate + reason + trade-offs)
      -> deterministic explanation

The engine itself is pure (no database) so it is independently testable and
can be invoked from anywhere (CLI, tests, or the FastAPI integration layer).

Public entrypoint: :func:`app.risk_engine.engine.evaluate_asset`.
"""

from app.risk_engine.config import RiskConfig, default_config
from app.risk_engine.engine import (
    AssetAssessment,
    evaluate_asset,
    evaluate_scan,
)
from app.risk_engine.types import (
    AlgorithmConcern,
    AssetInput,
    BusinessContext,
    MoscaAssessment,
    RiskLevel,
    MigrationPriority,
    RiskFactorBreakdown,
)

__all__ = [
    "RiskConfig",
    "default_config",
    "AssetAssessment",
    "evaluate_asset",
    "evaluate_scan",
    "AlgorithmConcern",
    "AssetInput",
    "BusinessContext",
    "MoscaAssessment",
    "RiskLevel",
    "MigrationPriority",
    "RiskFactorBreakdown",
]
