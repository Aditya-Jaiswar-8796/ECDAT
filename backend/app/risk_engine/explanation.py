"""Deterministic natural-language explanation builder.

Produces the human-readable `explanation` attached to every assessment. It is
built entirely from the already-computed factors — it never recomputes or adds
new information, so the explanation can never disagree with the numbers. This
is what makes the engine auditable and trustworthy.
"""

from __future__ import annotations

from app.risk_engine.types import (
    AlgorithmConcern,
    MoscaAssessment,
    RiskFactorBreakdown,
    RiskLevel,
)


def build_explanation(
    concern: AlgorithmConcern,
    breakdown: RiskFactorBreakdown,
    risk_level: RiskLevel,
    mosca: MoscaAssessment,
    key_size,
    data_lifetime,
    internet_exposure,
) -> str:
    """Compose a deterministic, factor-by-factor explanation string.

    Each sentence maps 1:1 to a named component in `breakdown`, so a reader can
    trace the final score back to its inputs.
    """
    parts: list = []

    # 1. Algorithm concern.
    if not concern.known:
        parts.append(
            f"Algorithm '{concern.algorithm}' is not in the reviewed mapping and was "
            "scored conservatively pending manual review."
        )
    else:
        key_note = f" (key size {key_size})" if key_size else " (key size unknown)"
        parts.append(f"{concern.algorithm}{key_note}: {concern.reason}")

    # 2. Data lifetime vs planning horizon.
    lifetime = data_lifetime if data_lifetime is not None else "unknown"
    lifetime_desc = (
        f"Data lifetime of {lifetime} years"
        if data_lifetime is not None
        else "Data lifetime is unknown and was defaulted conservatively"
    )
    parts.append(
        f"{lifetime_desc}; scores {breakdown.lifetime_score:.0f}/100 against "
        f"a {mosca.planning_horizon_years}-year planning horizon."
    )

    # 3. Business criticality.
    parts.append(
        f"Business criticality contributes {breakdown.criticality_score:.0f}/100."
    )

    # 4. Internet exposure.
    exp = "exposed to the internet" if internet_exposure else "not internet-exposed"
    parts.append(f"Asset is {exp}; exposure contributes {breakdown.exposure_score:.0f}/100.")

    # 5. Migration complexity.
    parts.append(
        f"Migration complexity contributes {breakdown.complexity_score:.0f}/100."
    )

    # 6. Mosca harvest-now-decrypt-later reasoning.
    if mosca.harvest_now_risk:
        parts.append(
            "Mosca check flags harvest-now-decrypt-later: a susceptible primitive protects "
            "long-lived/exposed data."
        )
    else:
        parts.append(
            "Mosca check: no active harvest-now-decrypt-later exposure detected."
        )

    # 7. Net reading of the level.
    parts.append(f"Weighted result: {risk_level} risk.")

    return " ".join(str(p) for p in parts)
