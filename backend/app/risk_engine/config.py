"""Risk engine configuration.

All numeric weights and thresholds are defined here, in one place, so the
scoring is fully transparent and easy to tune. There is no hidden/learned
weight anywhere — changing a number here deterministically changes the score.

**Planning horizon note:** the engine refuses to invent a quantum-capable
calendar date. Instead it works off a configurable `planning_horizon_years`
(how many years out an organisation plans protection against a future quantum
adversary). This is exactly the "Z" in Mosca's X + Y > Z framing, expressed in
years rather than a guessed date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Scoring weights — the deterministic mix that produces the 0-100 result.
# They must always sum to 1.0. Each is documented with its rationale so the
# result stays explainable.
_DEFAULT_WEIGHTS = {
    "algorithm": 0.40,  # Vulnerability of the primitive itself (Shor/Grover).
    "lifetime": 0.20,   # Secrecy lifetime vs. planning horizon (Mosca X).
    "criticality": 0.15,  # Business impact if the protected data is exposed.
    "exposure": 0.15,   # Reachability / harvestability of the data.
    "complexity": 0.10,  # Migration cost — slower migration raises urgency (Mosca Y).
}

# Mosca boost: an additive adjustment when a susceptible algorithm protects
# long-lived, exposed data (harvest-now-decrypt-later). Constant and small so
# it nudges, never dominates, the weighted score.
_MOSCA_MAX_BOOST = 12.0

# Risk-level thresholds over the 0-100 score (inclusive upper bound on LOW).
_THRESHOLDS = {
    "LOW": 25,
    "MEDIUM": 50,
    "HIGH": 75,
    "CRITICAL": 101,  # everything above HIGH falls into CRITICAL.
}


@dataclass
class RiskConfig:
    """Tunable, transparent configuration for one evaluation run."""

    weights: dict = field(default_factory=lambda: dict(_DEFAULT_WEIGHTS))
    # Risk-level thresholds over the 0-100 score (inclusive upper bound).
    thresholds: dict = field(default_factory=lambda: dict(_THRESHOLDS))
    # Years an org plans to protect against a functional quantum adversary.
    planning_horizon_years: int = 20
    # Conservative assumption when data lifetime is unknown: if we cannot say
    # how long data persists, we assume it must survive the full horizon.
    default_data_lifetime_years: Optional[int] = None
    # Assumed migration time for Mosca's Y term, by migration_complexity.
    migration_years: dict = field(
        default_factory=lambda: {"LOW": 1, "MEDIUM": 3, "HIGH": 5}
    )

    def __post_init__(self) -> None:
        """Validate invariants that keep the score deterministic and sane."""
        # The weighted components must fully explain the base score.
        if abs(sum(self.weights.values()) - 1.0) > 1e-6:
            raise ValueError(
                f"Risk weights must sum to 1.0, got {sum(self.weights.values())}"
            )
        # Horizon must be a positive number of years.
        if self.planning_horizon_years <= 0:
            raise ValueError("planning_horizon_years must be > 0")
        # A zero/negative default lifetime would short-circuit Mosca wrongly.
        if (
            self.default_data_lifetime_years is not None
            and self.default_data_lifetime_years < 0
        ):
            raise ValueError("default_data_lifetime_years must be >= 0")


def default_config() -> RiskConfig:
    """Return a fresh RiskConfig with the documented defaults."""
    return RiskConfig()


# Editable business-context remapping of criticality/complexity adjectives onto
# a 0-100 normalized score. Kept here so an analyst can retune impact values.
CRITICALITY_SCORE = {
    "LOW": 20,      # Little business impact if compromised.
    "MEDIUM": 50,   # Moderate impact.
    "HIGH": 75,     # Significant impact to a core business process.
    "CRITICAL": 100,  # Compromise could be organizationally severe.
}

COMPLEXITY_SCORE = {
    "LOW": 25,    # Simple swap, low coordination.
    "MEDIUM": 50, # Moderate library/API migration.
    "HIGH": 75,   # Substantial refactor / cross-team change.
}
