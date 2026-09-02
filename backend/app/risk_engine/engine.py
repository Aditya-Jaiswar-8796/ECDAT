"""Deterministic risk scoring engine.

Turns a CryptoAsset (plus optional editable business context) into a complete,
0-100, fully-explained risk assessment:

    asset -> [algorithm, lifetime, criticality, exposure, complexity]
           -> weighted 0-100 score
           -> risk_level
           -> migration_priority (P1..P4)
           -> Mosca-style assessment
           -> recommendation + deterministic explanation

The engine is a **pure function of its inputs**: identical inputs always yield
identical outputs. No LLM/ML is consulted for the authoritative score. All
weights/thresholds live in :mod:`app.risk_engine.config` and all domain
knowledge (algorithm vulnerability + recommendations) lives in
:mod:`app.risk_engine.algorithms` — editable independently of this file.
"""

from __future__ import annotations

from typing import Iterable, Optional

import app.risk_engine.algorithms as algo
import app.risk_engine.explanation as ex
from app.risk_engine.config import (
    COMPLEXITY_SCORE,
    CRITICALITY_SCORE,
    RiskConfig,
    default_config,
)
from app.risk_engine.types import (
    AlgorithmConcern,
    AssetAssessment,
    AssetInput,
    BusinessContext,
    MoscaAssessment,
    RiskFactorBreakdown,
)


def resolve_lifetime(
    data_lifetime_years: Optional[int],
    default_lifetime: Optional[int],
    planning_horizon_years: int,
) -> Optional[int]:
    """Apply the single, documented missing-value policy for data lifetime.

    Resolution order:
      1. explicit scanner/analyst lifetime (used as-is);
      2. configured default lifetime (`config.default_data_lifetime_years`);
      3. otherwise the planning horizon itself — the conservative assumption
         that we cannot prove the data is short-lived, so we must protect it
         for the full planning window.

    Returns None only when there is genuinely no signal and no horizon context
    (planning_horizon <= 0 is already rejected by the config).
    """
    if data_lifetime_years is not None:
        return data_lifetime_years
    if default_lifetime is not None:
        return default_lifetime
    # Conservative default: assume the data must survive the full horizon.
    return planning_horizon_years


def lifetime_score(
    data_lifetime_years: Optional[int],
    planning_horizon_years: int,
    default_lifetime: Optional[int],
) -> float:
    """Map data lifetime onto a normalized 0-100 'secrecy persistence' score.

    Uses the planning horizon as the ceiling: data that must persist for (or
    past) the full planning horizon scores highest (100). Missing values are
    resolved by :func:`resolve_lifetime` (conservative-worst-case).
    """
    lifetime = resolve_lifetime(
        data_lifetime_years, default_lifetime, planning_horizon_years
    )
    if lifetime is None or lifetime <= 0:
        return 0.0
    # Cap at the horizon so the ratio stays in [0, 1].
    horizon = max(1, planning_horizon_years)
    return max(0.0, min(100.0, (lifetime / horizon) * 100.0))


def criticality_to_score(criticality: str) -> float:
    """Map the business-criticality adjective to a 0-100 contribution."""
    return float(CRITICALITY_SCORE.get(criticality.upper(), 50.0))


def complexity_to_score(complexity: str) -> float:
    """Map migration complexity to a 0-100 contribution (higher = more urgency)."""
    return float(COMPLEXITY_SCORE.get(complexity.upper(), 50.0))


def derive_risk_level(score_100: float, thresholds: dict) -> str:
    """Derive LOW/MEDIUM/HIGH/CRITICAL from the 0-100 score.

    Thresholds are inclusive upper-bound per bucket (see config). The mapping
    is monotonic and table-driven so retuning thresholds is a one-line change.
    """
    for level, bound in thresholds.items():
        if score_100 <= bound:
            return level
    return "CRITICAL"


def derive_priority(
    score_100: float,
    criticality: str,
) -> tuple[str, int]:
    """Derive migration priority (P1..P4) + bucket label.

    Priority reflects both the raw risk and the business criticality of the
    asset (a critical asset gets bumped even at equal score). Returns
    (bucket_label, tier) where tier is the numeric P1..P4 value.
    """
    # Start from the raw score bands.
    if score_100 >= 75:
        tier = 1
    elif score_100 >= 50:
        tier = 2
    elif score_100 >= 25:
        tier = 3
    else:
        tier = 4

    # Criticality escalation: a business-critical asset with at least medium
    # risk jumps one tier (can't go below P1).
    if criticality.upper() == "CRITICAL" and score_100 >= 50 and tier > 1:
        tier -= 1

    # Map tier -> canonical bucket vocabulary used across the team.
    label = {1: "URGENT", 2: "HIGH", 3: "MEDIUM", 4: "LOW"}[tier]
    return label, tier


def build_mosca(
    concern: AlgorithmConcern,
    data_lifetime: Optional[int],
    planning_horizon: int,
    migration_years: int,
    internet_exposure: bool,
    default_lifetime: Optional[int] = None,
) -> MoscaAssessment:
    """Build the Mosca-style assessment.

    Mosca: an asset is at risk if it must protect secret data for X years and
    migration takes Y years, while a quantum adversary is expected within Z
    years (X + Y > Z). Here Z = configurable planning horizon.

    Harvest-now-decrypt-later is only relevant if the primitive is susceptible
    AND the data lives long enough to overlap the horizon AND it is exposed.
    Missing lifetimes are resolved via the conservative shared policy.
    """
    x = resolve_lifetime(data_lifetime, default_lifetime, planning_horizon) or 0
    # Mosca overlap check: the data must remain protected for X years while a
    # quantum adversary may appear within Z (planning horizon), and migration
    # takes Y years => at risk when X + Y > Z.
    risk = x + migration_years > planning_horizon

    readable_life = data_lifetime if data_lifetime is not None else "unknown"

    if concern.is_post_quantum:
        statement = (
            "Primitive is already post-quantum ready; no harvest-now risk even with "
            "long data lifetime."
        )
        diagnostic = "no-risk-pq-safe"
        harvest = False
    elif risk and internet_exposure and concern.susceptibility > 0:
        statement = (
            f"Harvest-now-decrypt-later: susceptible {concern.algorithm} protects data "
            f"kept {readable_life} years (~{x}+{migration_years} > {planning_horizon} yr "
            "horizon), and it is internet-exposed, so ciphertext can be captured today "
            "and decrypted once a quantum computer exists."
        )
        diagnostic = "harvest-now-decrypt-later"
        harvest = True
    elif risk:
        statement = (
            f"Long-lived susceptible data ({readable_life} years) overlaps the "
            f"{planning_horizon}-year horizon; monitor transition."
        )
        diagnostic = "long-lived-susceptible"
        harvest = False
    else:
        statement = (
            "No harvest-now-decrypt-later exposure detected for this asset."
        )
        diagnostic = "no-active-risk"
        harvest = False

    return MoscaAssessment(
        data_lifetime=data_lifetime,
        planning_horizon_years=planning_horizon,
        migration_years=migration_years,
        harvest_now_risk=harvest,
        risk_statement=statement,
        diagnostic=diagnostic,
    )


def compute_breakdown(
    concern: AlgorithmConcern,
    data_lifetime: Optional[int],
    planning_horizon: int,
    default_lifetime: Optional[int],
    internet_exposure: bool,
    criticality: str,
    complexity: str,
    mosca: MoscaAssessment,
) -> RiskFactorBreakdown:
    """Compute the weighted component breakdown plus Mosca boost.

    The base score is the weighted sum of the five components; the Mosca boost
    is an additive, capped adjustment applied only when a harvest-now risk is
    present. The returned breakdown exposes every term so the result is auditable.
    """
    alg_score = concern.vulnerability_score
    # The lifetime and exposure components only describe harvest-now risk when
    # the primitive is actually quantum-susceptible. A PQ-safe primitive (e.g.
    # AES-256, ML-KEM) has nothing to harvest, so its lifetime/exposure do not
    # contribute PQ risk — this keeps a green asset green regardless of how
    # long its data persists or whether it is internet-exposed.
    harvestable = concern.susceptibility > 0.0
    life_score = (
        lifetime_score(data_lifetime, planning_horizon, default_lifetime)
        if harvestable
        else 0.0
    )
    crit_score = criticality_to_score(criticality)
    exp_score = 100.0 if (internet_exposure and harvestable) else 0.0
    comp_score = complexity_to_score(complexity)

    # Mosca boost: additive, bounded, zero unless actively being harvested.
    boost = 0.0
    if mosca.harvest_now_risk:
        # Susceptibility scales the boost; cap keeps it a nudge, not a veto.
        boost = concern.susceptibility * 12.0
    return RiskFactorBreakdown(
        algorithm_score=alg_score,
        lifetime_score=life_score,
        criticality_score=crit_score,
        exposure_score=exp_score,
        complexity_score=comp_score,
        mosca_boost=min(12.0, boost),
    )


def _final_score(breakdown: RiskFactorBreakdown, weights: dict) -> float:
    """Combine the weighted base and the Mosca boost, clamped to [0, 100]."""
    base = (
        weights["algorithm"] * breakdown.algorithm_score
        + weights["lifetime"] * breakdown.lifetime_score
        + weights["criticality"] * breakdown.criticality_score
        + weights["exposure"] * breakdown.exposure_score
        + weights["complexity"] * breakdown.complexity_score
    )
    return max(0.0, min(100.0, base + breakdown.mosca_boost))


def evaluate_asset(
    asset: AssetInput,
    config: Optional[RiskConfig] = None,
    business_context: Optional[BusinessContext] = None,
) -> AssetAssessment:
    """Evaluate a single asset through the full deterministic pipeline.

    This is the authoritative entrypoint. Every branch is deterministic and
    documented; the only external knowledge are the algorithm/recommendation
    mappings (algorithms.py) and the config numbers (config.py).
    """
    config = config or default_config()
    # Apply editable business overrides first so hand-tuned context wins.
    resolved = business_context.effective(asset) if business_context else asset

    # 1. Profile the algorithm (concern + suggested PQ target). Key size is
    #    passed through because it matters for AES (Grover halves key length).
    concern = algo.profile_algorithm(resolved.algorithm, resolved.key_size)

    # 2. Mosca-style reasoning (needs lifetime/horizon/migration/exposure).
    mosca = build_mosca(
        concern=concern,
        data_lifetime=resolved.data_lifetime_years,
        planning_horizon=config.planning_horizon_years,
        migration_years=config.migration_years[
            resolved.migration_complexity.upper()
        ],
        internet_exposure=resolved.internet_exposure,
        default_lifetime=config.default_data_lifetime_years,
    )

    # 3. Weighted component breakdown + Mosca boost.
    breakdown = compute_breakdown(
        concern=concern,
        data_lifetime=resolved.data_lifetime_years,
        planning_horizon=config.planning_horizon_years,
        default_lifetime=config.default_data_lifetime_years,
        internet_exposure=resolved.internet_exposure,
        criticality=resolved.business_criticality,
        complexity=resolved.migration_complexity,
        mosca=mosca,
    )

    # 4. Final 0-100 score and its 0-10 API variant.
    score_100 = _final_score(breakdown, config.weights)
    score_10 = round(score_100 / 10.0, 2)

    # 5. Risk level + migration priority (P1..P4).
    level = derive_risk_level(score_100, config.thresholds)
    priority_label, priority_tier = derive_priority(
        score_100, resolved.business_criticality
    )

    # 6. Recommendation (candidate + reason + trade-offs) from the mapping.
    rec = algo.recommendation_for(concern, resolved.operation, resolved.key_size)
    recommendation = rec["recommendation"] if rec else "No migration required."

    # 7. Deterministic explanation assembled from the computed factors.
    explanation = ex.build_explanation(
        concern=concern,
        breakdown=breakdown,
        risk_level=level,
        mosca=mosca,
        key_size=resolved.key_size,
        data_lifetime=resolved.data_lifetime_years,
        internet_exposure=resolved.internet_exposure,
    )

    return AssetAssessment(
        asset_id=resolved.id,
        score_100=round(score_100, 2),
        score_10=score_10,
        risk_level=level,
        migration_priority=priority_label,
        priority_tier=priority_tier,
        mosca=mosca,
        breakdown=breakdown,
        recommendation=recommendation,
        explanation=explanation,
        suggested_target=rec["target"] if rec else None,
        effort_estimate=rec["effort"] if rec else None,
        trade_offs=rec["trade_offs"] if rec else [],
        reason=rec["explanation"] if rec else concern.reason,
        algorithm_known=concern.known,
    )


def evaluate_scan(
    assets: Iterable[AssetInput],
    config: Optional[RiskConfig] = None,
    business_contexts: Optional[dict[str, BusinessContext]] = None,
) -> list[AssetAssessment]:
    """Evaluate a whole scan deterministically.

    `assets` may be any iterable (list from the DB, etc.). Optional per-asset
    business contexts keyed by asset id let an analyst override specific rows.
    """
    config = config or default_config()
    contexts = business_contexts or {}
    results: list[AssetAssessment] = []
    for asset in assets:
        ctx = contexts.get(asset.id)
        results.append(evaluate_asset(asset, config=config, business_context=ctx))
    return results
