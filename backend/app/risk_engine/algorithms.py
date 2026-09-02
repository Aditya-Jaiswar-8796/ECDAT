"""Algorithm profiling knowledge base.

This is the **editable recommendation / vulnerability mapping** that Member 2 is
expected to supply as "reviewed mappings". M2 material is not yet available in
the repo, so this module ships a scoped, transparent baseline grounded in the
public NIST post-quantum transition guidance (NIST FIPS 203/204/205) and the
well-known susceptibility of primitives to Shor's / Grover's algorithms.

**Lifecycle / swap policy:** When M2's reviewed mappings arrive, update the
`_ALGORITHM_PROFILES` table and the `_RECOMMENDATION_MAP` below. The rest of the
engine reads through `profile_algorithm()` and `recommendation_for()` and needs
no other changes — the mappings are deliberately the only domain-knowledge
dependency of the scoring logic.

No library is imported here: this is pure data + pure analytic functions so the
engine stays dependency-light and deterministic.
"""

from __future__ import annotations

from typing import Optional

from app.risk_engine.types import AlgorithmConcern

# --------------------------------------------------------------------------- #
# Vulnerability profile per detected algorithm family.
# --------------------------------------------------------------------------- #
# Each profile carries:
#   category       - one of asymmetric/symmetric/hash/mac/unknown
#   susceptibility - 0..1 factor used by the Mosca boost (how strongly a future
#                    quantum adversary erodes this primitive).
#   vuln_base      - the algorithm-contribution to risk (0-100) BEFORE key-size
#                    adequacy is considered.
#   known          - whether the algorithm is recognised.
#
# Rationale (kept as the domain note each profile carries):
#   * Asymmetric PKC (RSA/ECC/ECDSA/DSA/DH/ECDH) is broken by Shor's algorithm
#     => highest concern.
#   * Symmetric AES is only weakened ~square-root by Grover => low concern,
#     and AES-256 already exceeds the usual PQ guidance (key-size logic lives
#     in `_profile_aes`).
#   * Hash pre-image is weakened ~cube-root by Grover => moderate (needs longer
#     output for the same security margin).
#   * HMAC/MAC security is tied to the underlying hash / key => low-moderate.
_ASYM_PROFILE = {
    "category": "asymmetric",
    "susceptibility": 1.0,
    "vuln_base": 80.0,
    "known": True,
    "note": "Public-key crypto (RSA/ECC) is broken by Shor's algorithm at scale.",
    "suggested_target": None,  # filled at recommendation time by operation.
    "is_post_quantum": False,
}

# SHA2 family: weakened by Grover but not catastrophic; larger outputs help.
_HASH_PROFILE = {
    "category": "hash",
    "susceptibility": 0.4,
    "vuln_base": 40.0,
    "known": True,
    "note": "Hash preimage/search weakened ~cube-root by Grover; prefer >=256-bit outputs.",
    "suggested_target": None,
    "is_post_quantum": False,
}

_MAC_PROFILE = {
    "category": "mac",
    "susceptibility": 0.25,
    "vuln_base": 30.0,
    "known": True,
    "note": "MAC security tracks the underlying hash/key; use a 256-bit key.",
    "suggested_target": None,
    "is_post_quantum": False,
}

# Recognised NIST-selected post-quantum algorithms => already safe, lowest risk.
_PQ_PROFILES = {
    "ML-KEM", "MLKEM", "CRYSTALS-KYBER", "KYBER", "ML-KEM-512", "ML-KEM-768",
    "ML-KEM-1024", "ML-DSA", "CRYSTALS-DILITHIUM", "DILITHIUM", "SLH-DSA",
    "SPHINCS+", "SPHINCS", "FALCON", "X25519MLKEM768", "MLKEM768-X25519",
}

# Recognition by exact or normalised (upper) algorithm name -> profile builder.
# Unknown names fall through to a conservative 'unknown' profile.
# NOTE: AES variants are handled by `_profile_aes` (key-size aware) before this
# table is consulted, so they are intentionally absent here.
_ALGORITHM_PROFILES = {
    "RSA": _ASYM_PROFILE,
    "RSA-PSS": _ASYM_PROFILE,
    "RSA-OAEP": _ASYM_PROFILE,
    "EC": _ASYM_PROFILE,
    "ECDSA": _ASYM_PROFILE,
    "ECDH": _ASYM_PROFILE,
    "ECIES": _ASYM_PROFILE,
    "DSA": _ASYM_PROFILE,
    "DH": _ASYM_PROFILE,
    "DIFFIE-HELLMAN": _ASYM_PROFILE,
    "X25519": _ASYM_PROFILE,
    "X448": _ASYM_PROFILE,
    "ED25519": _ASYM_PROFILE,
    "ED448": _ASYM_PROFILE,
    "SHA256": {**_HASH_PROFILE, "vuln_base": 20.0, "susceptibility": 0.2, "note": "SHA-256 preimage search ~2^85 under Grover; PQ margin is comfortable."},
    "SHA-256": {**_HASH_PROFILE, "vuln_base": 20.0, "susceptibility": 0.2, "note": "SHA-256 preimage search ~2^85 under Grover; PQ margin is comfortable."},
    "SHA384": {**_HASH_PROFILE, "vuln_base": 20.0, "susceptibility": 0.2, "note": "SHA-384 preimage search far beyond Grover reach; PQ margin is ample."},
    "SHA-384": {**_HASH_PROFILE, "vuln_base": 20.0, "susceptibility": 0.2, "note": "SHA-384 preimage search far beyond Grover reach; PQ margin is ample."},
    "SHA512": {**_HASH_PROFILE, "vuln_base": 20.0, "susceptibility": 0.2, "note": "SHA-512 preimage search far beyond Grover reach; PQ margin is ample."},
    "SHA-512": {**_HASH_PROFILE, "vuln_base": 20.0, "susceptibility": 0.2, "note": "SHA-512 preimage search far beyond Grover reach; PQ margin is ample."},
    "SHA3": {**_HASH_PROFILE, "vuln_base": 20.0, "susceptibility": 0.2, "note": "SHA-3 preimage search far beyond Grover reach; PQ margin is ample."},
    "SHA-3": {**_HASH_PROFILE, "vuln_base": 20.0, "susceptibility": 0.2, "note": "SHA-3 preimage search far beyond Grover reach; PQ margin is ample."},
    "MD5": {**_HASH_PROFILE, "vuln_base": 60.0, "susceptibility": 0.8, "note": "MD5 is cryptographically broken even classically; not PQ-relevant, replace it."},
    "SHA1": {**_HASH_PROFILE, "vuln_base": 55.0, "susceptibility": 0.7, "note": "SHA-1 collision attacks; replace regardless of PQ."},
    "HMAC": _MAC_PROFILE,
    "HMAC-SHA256": _MAC_PROFILE,
    "HMAC-SHA512": _MAC_PROFILE,
    "PBKDF2": _MAC_PROFILE,
    "BCRYPT": _MAC_PROFILE,
    "ARGON2": _MAC_PROFILE,
}

# --------------------------------------------------------------------------- #
# Function: resolve the concern profile for a detected algorithm.
# --------------------------------------------------------------------------- #


def profile_algorithm(algorithm: str, key_size: Optional[int] = None) -> AlgorithmConcern:
    """Deterministically profile a raw algorithm string into an AlgorithmConcern.

    Handles unknown values by falling back to a conservative 'unknown' profile
    so a scan never crashes on an unrecognised primitive — it is simply flagged
    for manual review (the only non-data decision point, and it is explicit).

    `key_size` is used to special-case AES (Grover halves the effective key
    length, so AES-128 is weakened while AES-256 keeps its margin). Other
    families use the fixed profiles below.
    """
    # Normalise case so 'rsa' == 'RSA' == 'Rsa'.
    key = (algorithm or "").strip().upper()

    # Recognised NIST post-quantum algorithm => already PQ safe.
    if key in _PQ_PROFILES or any(p in key for p in _PQ_PROFILES):
        return AlgorithmConcern(
            algorithm=algorithm,
            category="asymmetric",
            known=True,
            vulnerability_score=5.0,
            susceptibility=0.0,
            reason="Detected NIST-selected post-quantum algorithm (already PQ-ready).",
            suggested_target=None,
            is_post_quantum=True,
        )

    # AES is profile-sensitive to its key length (only relevant knob for
    # Grover's attack: AES-128 -> 64 effective bits, AES-256 -> 128 bits).
    if key == "AES" or key.startswith("AES-"):
        return _profile_aes(algorithm, key_size)

    profile = _ALGORITHM_PROFILES.get(key)
    if profile is not None:
        return AlgorithmConcern(
            algorithm=algorithm,
            category=profile["category"],
            known=True,
            vulnerability_score=profile["vuln_base"],
            susceptibility=profile["susceptibility"],
            reason=profile["note"],
            suggested_target=None,
            is_post_quantum=profile["is_post_quantum"],
        )

    # Unknown algorithm: keep it deterministic and conservative, but clearly
    # flag it so an analyst can review rather than silently scoring 0.
    return AlgorithmConcern(
        algorithm=algorithm,
        category="unknown",
        known=False,
        vulnerability_score=50.0,
        susceptibility=0.6,
        reason=(
            "Unrecognised algorithm; scored at a conservative mid-level pending "
            "manual review. Not treated as PQ-safe."
        ),
        suggested_target=None,
        is_post_quantum=False,
    )


def _profile_aes(algorithm: str, key_size: Optional[int]) -> AlgorithmConcern:
    """Profile the AES family by the actual key size in use.

    Grover's algorithm halves the effective symmetric key length, so:
      - AES-256 keeps a 128-bit PQ margin   => PQ-safe (green).
      - AES-192 keeps a 96-bit margin       => acceptable, low concern.
      - AES-128 drops to ~64 bits           => real PQ concern, recommend AES-256.
    """
    bits = key_size
    # Fall back to parsing the algorithm string when key_size was not supplied
    # (e.g. "AES-256" rather than key_size=256).
    if bits is None and algorithm.upper().startswith("AES-"):
        try:
            bits = int(algorithm.upper().split("-")[1])
        except (ValueError, IndexError):
            bits = None

    if bits is not None and bits >= 256:
        return AlgorithmConcern(
            algorithm=algorithm,
            category="symmetric",
            known=True,
            vulnerability_score=5.0,
            susceptibility=0.0,
            reason="AES-256 retains a 128-bit PQ security margin even under Grover.",
            suggested_target=None,
            is_post_quantum=True,
        )
    if bits is not None and bits == 192:
        return AlgorithmConcern(
            algorithm=algorithm,
            category="symmetric",
            known=True,
            vulnerability_score=20.0,
            susceptibility=0.2,
            reason="AES-192 keeps a ~96-bit margin under Grover; acceptable but monitor.",
            suggested_target="AES-256",
            is_post_quantum=False,
        )
    if bits == 128:
        return AlgorithmConcern(
            algorithm=algorithm,
            category="symmetric",
            known=True,
            vulnerability_score=45.0,
            susceptibility=0.6,
            reason="AES-128 halves to ~64 effective bits under Grover; prefer AES-256.",
            suggested_target="AES-256",
            is_post_quantum=False,
        )
    # Unknown AES key size: be conservative but not catastrophic.
    return AlgorithmConcern(
        algorithm=algorithm,
        category="symmetric",
        known=True,
        vulnerability_score=30.0,
        susceptibility=0.4,
        reason="AES with unknown key size; assume a mid-level PQ concern until confirmed.",
        suggested_target="AES-256",
        is_post_quantum=False,
    )


# --------------------------------------------------------------------------- #
# Recommendation mapping.
# --------------------------------------------------------------------------- #
# M2's reviewed mapping is expected to replace/extend these entries. The shape
# is deliberately standard so it is easy to bulk-edit:
#   operation -> (recommendation, suggested_target, explanation, effort)
# Plus optional trade-off notes surfaced to the dashboard.


def _smartcard_target(operation: str, key_size: Optional[int]) -> str:
    """Pick a concrete PQ replacement target for an asymmetric operation."""
    # Key-exchange and signing have different NIST-selected candidates.
    if operation == "keyexchange":
        return "ML-KEM-768"
    if operation == "signing":
        return "ML-DSA-44"
    # Generic / encryption: default to a KEM (most asymmetric budget is KEM).
    # RSA below 2048 is short even classically, so we still suggest the KEM.
    if operation == "encryption":
        return "ML-KEM-768"
    return "ML-KEM-768"


# Detailed recommended migration for each asymmetric operation. Used to build
# the recommendation with a human-readable reason + trade-offs.
_ASYM_RECOMMENDATION = {
    "keyexchange": {
        "recommendation": "Replace {alg} key exchange with ML-KEM (CRYSTALS-Kyber), e.g. ML-KEM-768.",
        "target": "ML-KEM-768",
        "explanation": (
            "{alg} key establishment is broken by Shor's algorithm; ML-KEM is the "
            "NIST-selected PQ KEM standardized in FIPS 203."
        ),
        "trade_offs": [
            "Larger public keys and ciphertexts than ECDH (bandwidth cost).",
            "Library/toolchain must ship a FIPS 203 implementation.",
            "Consider hybrid (e.g. X25519 + ML-KEM) during transition for compat.",
        ],
        "effort": "2-4 weeks",
    },
    "signing": {
        "recommendation": "Replace {alg} signatures with ML-DSA (CRYSTALS-Dilithium) or SLH-DSA (SPHINCS+).",
        "target": "ML-DSA-44",
        "explanation": (
            "{alg} signatures are forgeable by Shor's algorithm; ML-DSA (FIPS 204) "
            "and SLH-DSA (FIPS 205) are the NIST-selected PQ signature schemes."
        ),
        "trade_offs": [
            "ML-DSA signatures are larger than ECDSA but fast to verify.",
            "SLH-DSA has small signatures but slower signing; pick by context.",
            "Certificate/key rotation plus client compatibility must be planned.",
        ],
        "effort": "2-4 weeks",
    },
    "encryption": {
        "recommendation": "Replace {alg} encryption/hybrid with ML-KEM (or hybrid X25519 + ML-KEM).",
        "target": "ML-KEM-768",
        "explanation": (
            "{alg} encryption (RSA/EC) is broken by Shor's algorithm; migrate to "
            "the NIST-selected ML-KEM for PQ key establishment."
        ),
        "trade_offs": [
            "ML-KEM is a KEM (key encapsulation), so wrap the existing symmetric "
            "cipher (e.g. AES-256) via the KEM rather than encrypt directly.",
            "Ciphertext/state size grows vs. RSA/EC.",
        ],
        "effort": "2-4 weeks",
    },
}


def recommendation_for(
    concern: AlgorithmConcern,
    operation: str,
    key_size: Optional[int],
) -> Optional[dict]:
    """Return a recommendation mapping for an algorithm/operation, or None.

    Returns None for already-PQ-safe algorithms (no migration needed) and for
    unknown algorithms (needs manual review, no canned remediation).
    """
    # Post-quantum-safe primitive: nothing to migrate.
    if concern.is_post_quantum:
        return {
            "recommendation": f"{concern.algorithm} is already post-quantum ready; no migration required.",
            "target": None,
            "explanation": "Detected NIST-selected PQ algorithm; already on the secured baseline.",
            "trade_offs": ["None — already PQ-ready."],
            "effort": "None",
        }

    # Unknown primitive: no safe canned recommendation, flag for review.
    if not concern.known:
        return {
            "recommendation": (
                f"Manual review required: unrecognised algorithm '{concern.algorithm}'. "
                "Confirm the primitive and its TLS/library context before planning PQ work."
            ),
            "target": None,
            "explanation": "Algorithm is not in the reviewed mapping; cannot auto-recommend a migration.",
            "trade_offs": ["Verify the actual primitive first; may already be PQ-safe."],
            "effort": "Review needed",
        }

    # Symmetric / hash / mac: generally safe with adequate key/output sizes.
    if concern.category in ("symmetric", "hash", "mac"):
        return {
            "recommendation": _symmetric_recommendation(concern, operation, key_size),
            # AES-128/unknown-size AES carry a concrete suggested target; other
            # symmetric/hash/mac primitives default to the AES-256 baseline.
            "target": concern.suggested_target or "AES-256",
            "explanation": concern.reason,
            "trade_offs": ["Symmetric/hash primitives need only adequate key/output size, not a PQ swap."],
            "effort": "Low",
        }

    # Asymmetric: the primary migration path, driven by operation.
    rec = _ASYM_RECOMMENDATION.get(
        operation, _ASYM_RECOMMENDATION["encryption"]
    ).copy()
    rec["recommendation"] = rec["recommendation"].format(alg=concern.algorithm)
    rec["explanation"] = rec["explanation"].format(alg=concern.algorithm)
    rec["target"] = _smartcard_target(operation, key_size)
    return rec


def _symmetric_recommendation(
    concern: AlgorithmConcern, operation: str, key_size: Optional[int]
) -> str:
    """Human-readable symmetric/hash/mac recommendation."""
    # AES with key < 256 bits is weakened by Grover; recommend the upgrade.
    # Handles both "AES" (with key_size) and "AES-128"/"AES-192" name forms.
    if concern.algorithm.upper().startswith("AES") and (key_size or 0) < 256:
        return "Upgrade AES to AES-256 to retain PQ security margin under Grover."
    if concern.category == "hash":
        return "Prefer SHA-256/SHA-384/SHA-512 (>=256-bit output) for PQ margin."
    if concern.category == "mac":
        return "Ensure HMAC uses a 256-bit key and a strong hash for PQ margin."
    return "Primitive is PQ-safe with adequate key size; no migration needed."
