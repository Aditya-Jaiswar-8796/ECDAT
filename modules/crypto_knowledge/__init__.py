"""Crypto knowledge base and methodology package (Member 2).

Reads the three authoritative JSON documents shipped in this directory:

- crypto_knowledge.json  - algorithm classifications (family, legacy status,
                          quantum concern, base risk score, fallback rules)
- methodology.json       - Mosca-style reasoning, configurable planning
                          horizon, risk factors, scoring and thresholds
- recommendations.json   - PQC guidance, hybrid migration, crypto-agility and
                          per-algorithm remediation actions

The package provides deterministic lookups and scoring helpers so the risk
engine (Member 5) and dashboard (Member 6) consume the same, validated data.
All classification content is owned by Member 2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_PACKAGE_DIR = Path(__file__).resolve().parent


def _load(filename: str) -> Dict[str, Any]:
    with (_PACKAGE_DIR / filename).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_algorithm_knowledge() -> Dict[str, Any]:
    """Return crypto_knowledge.json as parsed JSON."""
    return _load("crypto_knowledge.json")


def load_methodology() -> Dict[str, Any]:
    """Return methodology.json as parsed JSON."""
    return _load("methodology.json")


def load_recommendations() -> Dict[str, Any]:
    """Return recommendations.json as parsed JSON."""
    return _load("recommendations.json")


def resolve_algorithm(name: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve an M3 algorithm string to a knowledge-base entry.

    Lookup order: core id, core alias, extended alias. Returns None when the
    name is unknown; callers should then use fallback_rules by operation.
    """
    knowledge = load_algorithm_knowledge()
    if not name:
        return None

    for entry in knowledge["core_algorithms"]:
        if name == entry["id"] or name in entry.get("aliases", []):
            resolved = dict(entry)
            resolved["resolution"] = "core"
            return resolved

    extended = knowledge.get("extended_algorithms", {}).get("entries", {})
    if name in extended:
        entry = dict(extended[name])
        entry["resolution"] = "extended"
        return entry
    return None


def canonical_operation(m3_operation: Optional[str]) -> Dict[str, Any]:
    """Map an M3 operation token to its canonical primitive metadata."""
    mapping = load_methodology()["m3_operation_mapping"]["mapping"]
    if m3_operation in mapping:
        return mapping[m3_operation]
    if m3_operation in {"hash", "keyexchange"}:
        # Historical aliases from early contract examples.
        if m3_operation == "hash":
            return mapping["hashing"]
        return mapping["keyexchange"]
    return {"canonical": "unknown", "families": [], "family_hint": "none",
            "note": f"Unmapped M3 operation: {m3_operation}"}


def find_fallback(m3_operation: Optional[str]) -> Dict[str, Any]:
    """Return the fallback classification rule for an unresolvable algorithm."""
    knowledge = load_algorithm_knowledge()
    op = m3_operation or "unknown"
    for rule in knowledge["fallback_rules"]["rules"]:
        if rule["operation"] == op:
            return rule
    return next(r for r in knowledge["fallback_rules"]["rules"]
                if r["operation"] == "unknown")


def base_score_for(
    name: Optional[str],
    m3_operation: Optional[str] = None,
    key_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute the pre-factor base risk score for a scanner finding.

    Implements methodology.json risk_score_definition steps 1-2 (base score,
    key-size adjustment) but not the factor deltas, which are the caller's
    responsibility. Always clamps to the 0..10 scale.
    """
    methodology = load_methodology()

    find_algorithm = resolve_algorithm(name)
    if find_algorithm is None:
        rule = find_fallback(m3_operation)
        return {
            "algorithm": name,
            "resolution": "fallback",
            "family": rule.get("fallback_family"),
            "legacy_status": rule.get("fallback_legacy_status"),
            "base_risk_score": rule.get("fallback_base_risk_score", 0.0),
            "review_required": rule.get("review_required", True),
            "canonical_operation": canonical_operation(m3_operation)[
                "canonical"],
            "note": rule.get("note"),
        }

    base = float(find_algorithm["base_risk_score"])
    family = find_algorithm["family"]
    adjustment = 0.0

    ops = "unknown"
    if m3_operation:
        ops = canonical_operation(m3_operation)["canonical"]
    elif find_algorithm.get("uses"):
        ops = find_algorithm["uses"][0]

    adjustments = methodology["risk_score_definition"]["key_size_adjustments"]
    if family == "asymmetric":
        bucket = "ECC" if find_algorithm["id"] in {"ECC", "ECDSA", "ECDH"} \
            else "RSA"
        adjustment = _key_size_delta(adjustments.get(bucket, {}), key_size)
    elif family == "symmetric" and find_algorithm["id"] == "AES":
        adjustment = _key_size_delta(adjustments["AES"], key_size)

    raw = min(10.0, max(0.0, base + adjustment))
    return {
        "algorithm": find_algorithm["id"],
        "resolution": find_algorithm.get("resolution", "core"),
        "family": family,
        "legacy_status": find_algorithm["legacy_status"],
        "base_risk_score": round(raw, 1),
        "review_required": False,
        "canonical_operation": ops,
        "note": None,
    }


def _key_size_delta(table: Dict[str, float], key_size: Optional[int]) -> float:
    if key_size is None:
        return 0.0
    sizes = sorted(int(s) for s in table)
    nearest = min(sizes, key=lambda s: abs(s - key_size))
    return float(table[str(nearest)])


def risk_level_for(score: float) -> str:
    """Map a 0..10 score to LOW | MEDIUM | HIGH | CRITICAL."""
    thresholds = load_methodology()["risk_level_thresholds"]
    for level, band in thresholds.items():
        if band["min"] <= score <= band["max"]:
            return level
    return "CRITICAL"


__all__ = [
    "load_algorithm_knowledge",
    "load_methodology",
    "load_recommendations",
    "resolve_algorithm",
    "canonical_operation",
    "find_fallback",
    "base_score_for",
    "risk_level_for",
]