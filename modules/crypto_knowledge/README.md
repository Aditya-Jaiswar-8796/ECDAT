# ECDAT Crypto Knowledge Base + Methodology (Member 2)

Owned by the **Cryptography + PQC Technical Authority (Member 2)**. This
package is the single source of truth for how ECDAT classifies cryptographic
primitives and for how risk and migration decisions are derived.

## Deliverables

| File | Purpose |
| --- | --- |
| `crypto_knowledge.json` | Algorithm classifications: family, primitive/use, quantum concern, legacy status, base risk score, aliases (incl. M3 name variants), fallback rules for unresolvable findings. |
| `methodology.json` | Mosca-style reasoning (`X > Y + Z`), configurable planning horizon, transparent risk factors, scoring formula, thresholds, priority promotions, M3 operation mapping, M3/M5 review findings. |
| `recommendations.json` | PQC purpose/migration role/trade-offs (ML-KEM, ML-DSA), hybrid migration strategy, crypto-agility practices and per-algorithm remediation actions. |
| `__init__.py` | Deterministic loader + resolution/scoring helpers for Member 5 and Member 6. |
| `docs/crypto_methodology.md` | Human-readable methodology document describing the model, categories and governance. |

## Design invariants

- **No quantum arrival dates.** Timeline reasoning always uses the
  configurable `planning_horizon_years` parameter (an organisational
  assumption, never a prediction).
- **Transparent risk factors.** Every factor, weight and threshold is a field
  in `methodology.json`; nothing is inferred by downstream code.
- **Member 2 owns classifications.** Member 6 may format or validate these
  JSON files, but must not invent algorithms, families, legacy statuses,
  risk factors, weights or thresholds.
- **Lookup order** for an M3 algorithm string: core id -> core alias ->
  extended entry -> fallback rule by operation (with `review_required`).

## Quick use

```python
from modules.crypto_knowledge import (
    resolve_algorithm,
    base_score_for,
    risk_level_for,
    canonical_operation,
)

resolve_algorithm("DESede")        # -> 3DES core entry
base_score_for("AES", key_size=128)       # AES base 1.0 + 1.0 key-size = 2.0
base_score_for("RSA", "encryption", 1024) # 7.0 + 2.0 = 9.0
risk_level_for(9.0)                        # -> CRITICAL
canonical_operation("key_agreement")       # -> canonical key_establishment
```

## Validation

```bash
python -m unittest tests.test_crypto_knowledge -v
```

## Ownership / integration

- **Member 3** produces findings the knowledge base classifies; see the M3
  mapping review in `methodology.json` for the agreed vocabulary.
- **Member 5** loads the JSON files as read-only reference data and emits
  risk scores/priorities per `methodology.json`.
- **Member 6** renders these classifications; formatting only.