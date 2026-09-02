"""Output adapters: engine results -> team API payloads.

Member 1 owns the stable REST contract; the canonical schema defines
`risk_score` on a **0-10** scale while the engine's authoritative score is
**0-100**. These adapters convert engine output into:

* a :class:`RiskAssessment` (0-10 normalized) ready for
  ``POST /risks/ingest?scan_id=...`` (M1).
* a :class:`Recommendation` ready for ``POST /recommendations/ingest`` (M1).
* a rich M6 dashboard shape carrying the full 0-100 breakdown + explanation.

The normalization (0-100 -> 0-10) is the ONLY place the scale changes; the
engine itself always reasons in 0-100.
"""

from __future__ import annotations

from app.risk_engine.types import AssetAssessment
from app.schemas.risk import RiskAssessment
from app.schemas.recommendation import Recommendation


def to_risk_assessment(assessment: AssetAssessment) -> RiskAssessment:
    """Flatten one assessment into the canonical RiskAssessment payload.

    `risk_score` is the normalized 0-10 value required by the shared contract.
    """
    return RiskAssessment(
        asset_id=assessment.asset_id,
        # 0-100 -> 0-10 for the contract (score_10 is already rounded).
        risk_score=assessment.score_10,
        risk_level=assessment.risk_level,
        migration_priority=assessment.migration_priority,
        # Human-readable Mosca note surfaced to the dashboard's "Mosca" column.
        mosca_assessment=assessment.mosca.risk_statement,
        # Structured, machine-readable factor breakdown for analytics.
        factors={
            "score_100": assessment.score_100,
            "priority_tier": assessment.priority_tier,
            **assessment.breakdown.as_dict(),
            "mosca_diagnostic": assessment.mosca.diagnostic,
            "harvest_now": assessment.mosca.harvest_now_risk,
            "recommendation": assessment.recommendation,
        },
    )


def to_recommendation(assessment: AssetAssessment) -> Recommendation:
    """Flatten one assessment into the canonical Recommendation payload.

    Includes the concrete candidate target, a reason (explanation) and the
    trade-off notes, per the task's 'candidate + reason + trade-offs' rule.
    """
    return Recommendation(
        asset_id=assessment.asset_id,
        recommendation=assessment.recommendation,
        explanation=assessment.reason,
        suggested_target=assessment.suggested_target,
        effort_estimate=assessment.effort_estimate,
    )


def to_m6_view(assessment: AssetAssessment) -> dict:
    """Rich M6-facing view with the full 0-100 breakdown and explanation.

    The dashboard reads this when it needs more than the minimal columns
    (risk level, priority, Mosca text, explanation).
    """
    return {
        "asset_id": assessment.asset_id,
        "risk_score": assessment.score_10,
        "score_100": assessment.score_100,
        "risk_level": assessment.risk_level,
        "migration_priority": assessment.migration_priority,
        "priority_tier": assessment.priority_tier,
        "mosca_assessment": assessment.mosca.risk_statement,
        "mosca_diagnostic": assessment.mosca.diagnostic,
        "harvest_now": assessment.mosca.harvest_now_risk,
        "breakdown": assessment.breakdown.as_dict(),
        "recommendation": assessment.recommendation,
        "suggested_target": assessment.suggested_target,
        "effort_estimate": assessment.effort_estimate,
        "trade_offs": assessment.trade_offs,
        "reason": assessment.reason,
        "explanation": assessment.explanation,
        "algorithm_known": assessment.algorithm_known,
    }