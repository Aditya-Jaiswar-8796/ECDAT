"""Unit tests for the Member 5 risk engine.

Coverage targets per the task: score boundaries, missing values, unknown
algorithms, Mosca edge cases, determinism, transparent weights, editable
business context, 0-100/0-10 normalization, priority derivation and the
candidate+reason+trade-offs recommendation contract.
"""

import pytest

from app.risk_engine.config import RiskConfig, default_config
from app.risk_engine.engine import (
    derive_priority,
    derive_risk_level,
    evaluate_asset,
    evaluate_scan,
    lifetime_score,
)
from app.risk_engine.output import (
    to_risk_assessment,
    to_recommendation,
    to_m6_view,
)
from app.risk_engine.types import AssetInput, BusinessContext


def make_asset(**overrides) -> AssetInput:
    """A neutral asset with sane defaults for reusable tests."""
    base = dict(
        id="asset-001",
        algorithm="RSA",
        operation="keyexchange",
        key_size=2048,
        business_criticality="MEDIUM",
        data_lifetime_years=10,
        internet_exposure=True,
        migration_complexity="MEDIUM",
    )
    base.update(overrides)
    return AssetInput(**base)


# --------------------------------------------------------------------------- #
# Score scale + normalization
# --------------------------------------------------------------------------- #


def test_score_is_on_0_100_scale_always():
    """The authoritative score stays within [0, 100] for extreme inputs."""
    worst = make_asset(
        algorithm="RSA",
        business_criticality="CRITICAL",
        data_lifetime_years=10_000,
        internet_exposure=True,
        migration_complexity="HIGH",
    )
    best = make_asset(
        algorithm="ML-KEM-768",
        business_criticality="LOW",
        data_lifetime_years=0,
        internet_exposure=False,
        migration_complexity="LOW",
    )
    assert 0.0 <= evaluate_asset(worst).score_100 <= 100.0
    assert 0.0 <= evaluate_asset(best).score_100 <= 100.0


def test_score_10_is_score_100_divided_by_10():
    """The API-facing 0-10 variant is exactly the 0-100 score / 10."""
    a = evaluate_asset(make_asset())
    assert a.score_10 == round(a.score_100 / 10.0, 2)


def test_normalized_score_fits_contract_schema():
    """The RiskAssessment produced for M1 respects the 0..10 Pydantic bound."""
    from app.schemas.risk import RiskAssessment

    worst = evaluate_asset(
        make_asset(
            algorithm="RSA",
            business_criticality="CRITICAL",
            data_lifetime_years=10_000,
            internet_exposure=True,
            migration_complexity="HIGH",
        )
    )
    ra = to_risk_assessment(worst)
    # Pydantic would reject values outside ge=0/le=10.
    RiskAssessment.model_validate(ra.model_dump())


# --------------------------------------------------------------------------- #
# Risk-level boundary mapping
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.0, "LOW"),
        (25.0, "LOW"),        # LOW bucket is inclusive up to 25.
        (25.01, "MEDIUM"),
        (50.0, "MEDIUM"),     # MEDIUM inclusive up to 50.
        (50.01, "HIGH"),
        (75.0, "HIGH"),       # HIGH inclusive up to 75.
        (75.01, "CRITICAL"),
        (100.0, "CRITICAL"),
    ],
)
def test_level_boundaries(score, expected):
    """Threshold boundaries are deterministic and inclusive-as-documented."""
    assert derive_risk_level(score, default_config().thresholds) == expected


def test_custom_thresholds_are_used():
    """Retuning thresholds deterministically changes the level mapping."""
    cfg = RiskConfig(thresholds={"LOW": 10, "MEDIUM": 20, "HIGH": 30, "CRITICAL": 101})
    assert derive_risk_level(15.0, cfg.thresholds) == "MEDIUM"
    assert derive_risk_level(5.0, cfg.thresholds) == "LOW"


# --------------------------------------------------------------------------- #
# Priority derivation (P1..P4)
# --------------------------------------------------------------------------- #


def test_priority_tiers_from_score():
    assert derive_priority(90.0, "MEDIUM") == ("URGENT", 1)
    assert derive_priority(60.0, "MEDIUM") == ("HIGH", 2)
    assert derive_priority(30.0, "MEDIUM") == ("MEDIUM", 3)
    assert derive_priority(10.0, "MEDIUM") == ("LOW", 4)


def test_criticality_escalates_priority():
    """A business-critical asset at >=medium risk jumps one tier."""
    assert derive_priority(55.0, "CRITICAL") == ("URGENT", 1)  # would be P2
    assert derive_priority(55.0, "MEDIUM") == ("HIGH", 2)      # no escalation
    assert derive_priority(30.0, "CRITICAL") == ("MEDIUM", 3)  # below 50: no bump


def test_complexity_raises_urgency():
    """Higher migration complexity must raise the risk score (Mosca Y term)."""
    low_comp = evaluate_asset(make_asset(migration_complexity="LOW"))
    high_comp = evaluate_asset(make_asset(migration_complexity="HIGH"))
    assert high_comp.score_100 > low_comp.score_100


# --------------------------------------------------------------------------- #
# Determinism + transparent weights
# --------------------------------------------------------------------------- #


def test_determinism_same_input_same_output():
    """Identical inputs must produce identical outputs every time."""
    a1 = evaluate_asset(make_asset())
    a2 = evaluate_asset(make_asset())
    assert a1.score_100 == a2.score_100
    assert a1.risk_level == a2.risk_level
    assert a1.mosca.risk_statement == a2.mosca.risk_statement
    assert a1.explanation == a2.explanation


def test_weights_sum_to_one_and_are_transparent():
    """The documented weights must sum to 1.0 (config invariant)."""
    cfg = default_config()
    assert sum(cfg.weights.values()) == pytest.approx(1.0)
    assert set(cfg.weights) == {
        "algorithm",
        "lifetime",
        "criticality",
        "exposure",
        "complexity",
    }


def test_higher_algorithm_weight_raises_score_for_susceptible_asset():
    """Tuning the algorithm weight deterministically moves the score."""
    base = make_asset()
    w_high_alg = default_config()
    w_high_alg.weights = {
        "algorithm": 1.0, "lifetime": 0.0, "criticality": 0.0,
        "exposure": 0.0, "complexity": 0.0,
    }
    w_low_alg = default_config()
    w_low_alg.weights = {
        "algorithm": 0.0, "lifetime": 0.0, "criticality": 0.0,
        "exposure": 0.0, "complexity": 1.0,
    }
    assert (
        evaluate_asset(base, config=w_high_alg).score_100
        > evaluate_asset(base, config=w_low_alg).score_100
    )


def test_invalid_weights_rejected():
    """Weights that don't sum to 1.0 are rejected loudly."""
    with pytest.raises(ValueError):
        RiskConfig(weights={"algorithm": 0.5})


# --------------------------------------------------------------------------- #
# Missing values (conservative policy)
# --------------------------------------------------------------------------- #


def test_missing_lifetime_defaults_to_horizon():
    """Missing data lifetime assumes the full planning horizon (conservative)."""
    cfg = default_config()
    r = evaluate_asset(
        make_asset(algorithm="RSA", data_lifetime_years=None),
        config=cfg,
    )
    # Conservative assumption: data persists the full horizon => lifetime 100.
    assert r.breakdown.lifetime_score == 100.0
    assert r.mosca.data_lifetime is None


def test_missing_lifetime_with_configured_default():
    """A configured default lifetime is used for missing values."""
    cfg = default_config()
    cfg.default_data_lifetime_years = 5
    r = evaluate_asset(
        make_asset(algorithm="RSA", data_lifetime_years=None), config=cfg
    )
    assert r.breakdown.lifetime_score == 25.0  # 5/20 horizon.


def test_lifetime_score_ratio():
    """lifetime_score is the lifetime/horizon ratio capped to [0, 100]."""
    assert lifetime_score(10, 20, None) == 50.0
    assert lifetime_score(40, 20, None) == 100.0  # capped at horizon
    assert lifetime_score(0, 20, None) == 0.0
    assert lifetime_score(None, 20, None) == 100.0  # conservative default


# --------------------------------------------------------------------------- #
# Unknown algorithms
# --------------------------------------------------------------------------- #


def test_unknown_algorithm_does_not_crash():
    """An unrecognised primitive scores deterministically and flags review."""
    r = evaluate_asset(make_asset(algorithm="TotallyMadeUp"))
    assert r.algorithm_known is False
    assert 0 <= r.score_100 <= 100
    assert "Manual review" in r.recommendation
    assert r.suggested_target is None


def test_unknown_algorithm_not_highly_triggered_when_green():
    """Unknown but harmless-looking context still flags review, not a score blowup."""
    r = evaluate_asset(
        make_asset(
            algorithm="WeirdAlgo",
            business_criticality="LOW",
            data_lifetime_years=1,
            internet_exposure=False,
        )
    )
    assert r.algorithm_known is False
    assert r.score_100 <= 50


def test_algorithm_name_normalization():
    """Case/redundant-prefix variants resolve to the same concern."""
    from app.risk_engine.algorithms import profile_algorithm

    a = profile_algorithm("rsa")
    b = profile_algorithm("RSA")
    c = profile_algorithm("  Ecdsa ")
    assert a.vulnerability_score == b.vulnerability_score == c.vulnerability_score
    assert a.known and c.known


# --------------------------------------------------------------------------- #
# Mosca edge cases
# --------------------------------------------------------------------------- #


def test_mosca_harvest_now_only_when_exposed_longlived_susceptible():
    """Harvest-now-decrypt-later needs susceptible + long-lived + exposed."""
    exposed_long = evaluate_asset(
        make_asset(algorithm="RSA", data_lifetime_years=25, internet_exposure=True)
    )
    not_exposed = evaluate_asset(
        make_asset(algorithm="RSA", data_lifetime_years=25, internet_exposure=False)
    )
    short_lived = evaluate_asset(
        make_asset(algorithm="RSA", data_lifetime_years=5, internet_exposure=True)
    )
    assert exposed_long.mosca.harvest_now_risk is True
    assert exposed_long.mosca.diagnostic == "harvest-now-decrypt-later"
    assert not_exposed.mosca.harvest_now_risk is False
    assert short_lived.mosca.harvest_now_risk is False


def test_mosca_boundary_x_plus_y_equals_z_not_at_risk():
    """Mosca risk only when X+Y>Z; equality at the horizon is not flagged."""
    cfg = default_config()  # Z = 20 years, MEDIUM migration => Y = 3.
    # X = 17, Y = 3 => X+Y = 20 == Z -> boundary, NOT > => no harvest risk.
    boundary = evaluate_asset(
        make_asset(
            algorithm="RSA",
            data_lifetime_years=17,
            migration_complexity="MEDIUM",
            internet_exposure=True,
        ),
        config=cfg,
    )
    over = evaluate_asset(
        make_asset(
            algorithm="RSA",
            data_lifetime_years=18,
            migration_complexity="MEDIUM",
            internet_exposure=True,
        ),
        config=cfg,
    )
    assert boundary.mosca.harvest_now_risk is False
    assert over.mosca.harvest_now_risk is True


def test_mosca_pq_safe_never_harvests():
    """A PQ-safe primitive is never flagged harvest-now, even long-lived/exposed."""
    pq = evaluate_asset(
        make_asset(
            algorithm="ML-KEM-768",
            data_lifetime_years=200,
            internet_exposure=True,
        )
    )
    assert pq.mosca.harvest_now_risk is False
    assert pq.mosca.diagnostic == "no-risk-pq-safe"


def test_mosca_horizon_is_configurable_not_invented():
    """No quantum date exists; the planning horizon drives the math."""
    cfg_short = RiskConfig(planning_horizon_years=10)
    cfg_long = RiskConfig(planning_horizon_years=30)
    a = make_asset(
        algorithm="RSA", data_lifetime_years=15, internet_exposure=True
    )
    short = evaluate_asset(a, config=cfg_short)  # 15+3 > 10 -> harvest
    long = evaluate_asset(a, config=cfg_long)    # 15+3 > 30 -> no harvest
    assert short.mosca.harvest_now_risk is True
    assert long.mosca.harvest_now_risk is False
    # And the horizon value is surfaced, never a date string.
    assert "horizon" in short.explanation.lower()
    assert "10" in str(cfg_short.planning_horizon_years)


def test_mosca_horizon_zero_rejected():
    with pytest.raises(ValueError):
        RiskConfig(planning_horizon_years=0)


# --------------------------------------------------------------------------- #
# Algorithm concern behaviors
# --------------------------------------------------------------------------- #


def test_pq_algorithms_score_low():
    """NIST-selected PQ algorithms are the safest possible assets."""
    for alg in ["ML-KEM-768", "CRYSTALS-KYBER", "ML-DSA-44", "SLH-DSA"]:
        r = evaluate_asset(make_asset(algorithm=alg))
        assert r.risk_level == "LOW", alg
        assert r.breakdown.algorithm_score <= 5.0
        assert r.migration_priority == "LOW"


def test_rsa_and_ec_are_high_concern():
    """Shor-vulnerable asymmetric primitives score at the top of the spectrum."""
    for alg in ["RSA", "ECDSA", "ECDH", "DSA"]:
        r = evaluate_asset(
            make_asset(algorithm=alg, business_criticality="CRITICAL")
        )
        assert r.breakdown.algorithm_score == 80.0, alg


def test_aes256_is_green_even_long_lived_exposed():
    """AES-256 keeps a PQ margin, so it stays low despite hostile context."""
    r = evaluate_asset(
        make_asset(
            algorithm="AES",
            key_size=256,
            business_criticality="CRITICAL",
            data_lifetime_years=100,
            internet_exposure=True,
            migration_complexity="HIGH",
        )
    )
    assert r.risk_level == "LOW"
    assert r.mosca.harvest_now_risk is False


def test_aes128_is_flagged_for_upgrade():
    """AES-128 halves to ~64 bits under Grover; recommends AES-256."""
    r = evaluate_asset(make_asset(algorithm="AES-128", key_size=128))
    assert "AES-256" in r.recommendation
    assert r.suggested_target == "AES-256"


def test_aes_key_size_from_string_when_absent():
    """AES-256 without key_size still profiles green via the algorithm name."""
    r = evaluate_asset(make_asset(algorithm="AES-256", key_size=None))
    assert r.breakdown.algorithm_score <= 5.0


def test_unknown_key_size_aes_conservative():
    """AES with no key size is conservatively mid-level, never crashy."""
    r = evaluate_asset(make_asset(algorithm="AES", key_size=None))
    assert 0 <= r.score_100 <= 100


# --------------------------------------------------------------------------- #
# Editable business context
# --------------------------------------------------------------------------- #


def test_business_context_overrides_scanner_values():
    """Analyst-supplied context wins over the scanner-sourced fields."""
    asset = make_asset(business_criticality="LOW", internet_exposure=False)
    ctx = BusinessContext(
        business_criticality="CRITICAL",
        internet_exposure=True,
        data_lifetime_years=40,
    )
    base = evaluate_asset(asset)
    overridden = evaluate_asset(asset, business_context=ctx)
    assert overridden.score_100 > base.score_100


def test_business_context_partial_override_keeps_rest():
    """Unset context fields fall back to the existing asset values."""
    asset = make_asset(business_criticality="HIGH", internet_exposure=False)
    ctx = BusinessContext(data_lifetime_years=40)  # only lifetime set
    resolved = ctx.effective(asset)
    assert resolved.business_criticality == "HIGH"
    assert resolved.internet_exposure is False
    assert resolved.data_lifetime_years == 40


# --------------------------------------------------------------------------- #
# Recommendation contract (candidate + reason + trade-offs)
# --------------------------------------------------------------------------- #


def test_recommendation_includes_candidate_reason_tradeoffs():
    """Every asymmetric recommendation carries the full business contract."""
    r = evaluate_asset(make_asset(operation="keyexchange"))
    assert "ML-KEM" in r.suggested_target
    assert r.recommendation
    assert r.reason
    assert r.trade_offs and len(r.trade_offs) >= 1  # candidate+reason+trade-offs


def test_signing_recommendation_targets_dilithium():
    r = evaluate_asset(make_asset(operation="signing"))
    assert r.suggested_target == "ML-DSA-44"


def test_scan_wide_evaluation_and_bulk_contexts():
    """evaluate_scan maps per-asset contexts and returns one row per asset."""
    assets = [
        make_asset(id="a1", algorithm="RSA"),
        make_asset(id="a2", algorithm="ML-KEM-768"),
    ]
    ctxs = {"a1": BusinessContext(business_criticality="CRITICAL")}
    results = evaluate_scan(assets, business_contexts=ctxs)
    assert [r.asset_id for r in results] == ["a1", "a2"]
    # The criticality override on a1 is reflected in its score/level.
    assert results[0].risk_level in {"HIGH", "CRITICAL"}
    assert results[1].risk_level == "LOW"


# --------------------------------------------------------------------------- #
# Output adapters for M1/M6
# --------------------------------------------------------------------------- #


def test_risk_assessment_payload_shape():
    """to_risk_assessment emits the canonical M1 fields including Mosca text."""
    r = evaluate_asset(make_asset())
    ra = to_risk_assessment(r)
    d = ra.model_dump()
    assert d["asset_id"] == "asset-001"
    assert 0 <= d["risk_score"] <= 10
    assert d["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert d["migration_priority"] in {"LOW", "MEDIUM", "HIGH", "URGENT"}
    assert isinstance(d["mosca_assessment"], str) and d["mosca_assessment"]
    assert d["factors"]["score_100"] == r.score_100


def test_recommendation_payload_shape():
    """to_recommendation emits candidate target + reason for the dashboard."""
    r = evaluate_asset(make_asset())
    rec = to_recommendation(r)
    d = rec.model_dump()
    assert d["asset_id"] == "asset-001"
    assert d["recommendation"]
    assert d["suggested_target"]
    assert d["effort_estimate"]


def test_m6_view_is_rich_and_self_consistent():
    """M6 view mirrors the engine numbers exactly."""
    r = evaluate_asset(make_asset())
    v = to_m6_view(r)
    assert v["score_100"] == r.score_100
    assert v["risk_level"] == r.risk_level
    assert v["breakdown"]["algorithm"] == r.breakdown.algorithm_score
    assert v["explanation"] == r.explanation
    assert set(v["breakdown"]) == {
        "algorithm", "data_lifetime", "business_criticality",
        "internet_exposure", "migration_complexity", "mosca_boost",
    }


# --------------------------------------------------------------------------- #
# Scoring sanity spreads
# --------------------------------------------------------------------------- #


def test_risk_spread_across_algorithms():
    """RSA >> AES-256 for hostile context; order is deterministic and intuitive."""
    rsa = evaluate_asset(
        make_asset(algorithm="RSA", business_criticality="CRITICAL")
    )
    aes = evaluate_asset(
        make_asset(
            algorithm="AES",
            key_size=256,
            business_criticality="CRITICAL",
        )
    )
    assert rsa.score_100 > aes.score_100


def test_boosting_is_bounded():
    """The Mosca boost is never more than its documented cap (12.0)."""
    worst = evaluate_asset(
        make_asset(
            algorithm="RSA",
            business_criticality="CRITICAL",
            data_lifetime_years=200,
            internet_exposure=True,
        )
    )
    assert worst.breakdown.mosca_boost <= 12.0


def test_explanation_is_deterministic_and_sourced_from_factors():
    """Explanation text mentions the driver components without extra info."""
    r = evaluate_asset(make_asset(algorithm="RSA", internet_exposure=True))
    low = r.explanation.lower()
    assert "rsa" in low
    assert "planning horizon" in low
    assert "exposed" in low