# Member 5 — Risk Engine (RISK + MOSCA + MIGRATION PRIORITY + PQC/HYBRID RECOMMENDATION ENGINE)

Owner: **Member 5** (SIH 26164). Scope: `backend/app/risk_engine/` +
`backend/app/services/risk_service.py` + `backend/tests/`.

The engine is **deterministic** — no LLM/ML decides the authoritative risk
score. Identical inputs always produce identical outputs, every weight and
threshold is configurable and documented, and each asset ships a
machine-readable factor breakdown plus a natural-language explanation built
*from* those factors (never the other way around).

Plain-language contract for the rest of the team:

```
CryptoAsset
  -> algorithm concern + data lifetime + business criticality
     + internet exposure + migration complexity
  -> deterministic 0-100 score   (authoritative scale)
  -> risk_level   LOW/MEDIUM/HIGH/CRITICAL
  -> migration_priority P1/P2/P3/P4  (surfaced as URGENT/HIGH/MEDIUM/LOW)
  -> Mosca-style assessment  (harvest-now-decrypt-later)
  -> recommendation  (candidate + reason + trade-offs)
  -> deterministic explanation
```

---

## 1. Files

| File | Role |
|---|---|
| `backend/app/risk_engine/config.py` | Transparent weights, thresholds, planning horizon, criticality/complexity score maps |
| `backend/app/risk_engine/algorithms.py` | **Editable domain knowledge**: algorithm vulnerability profiles + recommendation mapping (M2 swap point) |
| `backend/app/risk_engine/engine.py` | The deterministic math: scoring, levels, priorities, Mosca |
| `backend/app/risk_engine/types.py` | Pure dataclasses (inputs / results), no framework deps |
| `backend/app/risk_engine/explanation.py` | Deterministic natural-language explanation from the factors |
| `backend/app/risk_engine/output.py` | Adapters to the canonical `RiskAssessment` / `Recommendation` schemas + M6 rich view |
| `backend/app/services/risk_service.py` | DB <-> engine bridge; persists results; `POST /risks/run` |
| `backend/tests/*` | Unit (engine), service (DB) and API (end-to-end) tests |

---

## 2. Scoring model (transparent, 0-100)

### 2.1 Weighted base (weights must sum to 1.0 — enforced)

| Component | Weight | What it measures |
|---|---|---|
| `algorithm` | 0.40 | Vulnerability of the primitive (Shor / Grover impact) |
| `lifetime` | 0.20 | Secrecy lifetime vs. planning horizon (Mosca's `X`) |
| `criticality` | 0.15 | Business impact if the protected data is exposed |
| `exposure` | 0.15 | How reachable / harvestable the asset is |
| `complexity` | 0.10 | Migration cost — slower migration raises urgency (Mosca's `Y`) |

The base score is the plain weighted sum. Two components are **susceptibility
gated**: `lifetime` and `exposure` only contribute when the primitive is
actually quantum-susceptible. A PQ-safe primitive (AES-256, ML-KEM, …) has
nothing to harvest, so longer lifetime / more exposure do not inflate its score
(a green asset stays green).

### 2.2 Mosca boost

When the Mosca check flags harvest-now-decrypt-later, an **additive, capped**
boost of `susceptibility × 12` (max 12.0) is applied. It nudges, never
dominates, the weighted score. `susceptibility` is the primitive's exposure to
a quantum adversary (1.0 for RSA/ECC, 0.6 for AES-128, 0.0 for PQ-safe).

### 2.3 Risk-level thresholds (over 0-100, inclusive upper bound)

| Level | Score range |
|---|---|
| LOW | 0 .. 25 |
| MEDIUM | 25.01 .. 50 |
| HIGH | 50.01 .. 75 |
| CRITICAL | 75.01 .. 100 |

### 2.4 Migration priority

Derived from the score band, with a criticality escalation:

| Base tier | Score | Bucket label | Meaning |
|---|---|---|---|
| P1 | >= 75 | URGENT | Act this sprint |
| P2 | >= 50 | HIGH | Plan into current/next sprint |
| P3 | >= 25 | MEDIUM | Schedule |
| P4 | < 25 | LOW | Monitor only |

A `CRITICAL`-business asset with score >= 50 jumps one tier (never below P1).
`URGENT/HIGH/MEDIUM/LOW` is the vocabulary already wired across
`RiskAssessment.migration_priority` and the dashboard.

---

## 3. Mosca-style assessment (no invented quantum dates)

The engine uses Mosca's framing with a **configurable planning horizon** as the
`Z` term — it never hard-codes a quantum-computer calendar date.

```
risk  <=>  X + Y > Z
    X = data_lifetime_years          (how long the secret must stay secret)
    Y = migration_years              (by migration_complexity: 1/3/5 years)
    Z = planning_horizon_years       (default 20, fully configurable)
```

Harvest-now-decrypt-later is flagged only when **all three** hold:
a susceptible primitive, data that outlives/overlaps the horizon, and internet
exposure. Boundary behavior is exact: `X + Y == Z` is **not** flagged (strict
inequality), covered by tests.

**Missing values policy (documented + tested):** missing `data_lifetime_years`
defaults conservatively to the full planning horizon (we cannot prove it is
short-lived); an explicit `RiskConfig.default_data_lifetime_years` overrides
that. Unknown algorithms are scored conservatively, flagged `algorithm_known:
false`, and routed to manual review rather than a canned recommendation.

---

## 4. Recommendation engine (PQC / hybrid) — candidate + reason + trade-offs

Recommendations are data-driven from the **editable mapping** in
`algorithms.py` and are surfaced as the three things M2/M6 asked for:

| Field | Content |
|---|---|
| `recommendation` | Concrete instruction (e.g. replace RSA key exchange with ML-KEM) |
| `suggested_target` | Candidate (e.g. `ML-KEM-768`, `ML-DSA-44`, `AES-256`) |
| `reason` / `explanation` | Why (Shor breaks RSA; NIST FIPS 203/204/205) |
| `trade_offs` | Cost/considerations (bandwidth, library support, hybrid during transition) |
| `effort_estimate` | e.g. `2-4 weeks` |

Current mapping defaults (public NIST selection, pending M2 review):

| Operation | Suggested target |
|---|---|
| key exchange | ML-KEM-768 (hybrid `X25519 + ML-KEM` noted during transition) |
| signing | ML-DSA-44 or SLH-DSA (SPHINCS+) |
| encryption | ML-KEM-based wrapping of AES-256 |
| AES < 256 bits | upgrade to AES-256 |

### 4.1 Where M2's reviewed mappings plug in

M2 material is not in the repo yet. Two tables in `algorithms.py` are the only
domain-knowledge dependency of the engine — replace/extend them when M2's
reviewed mapping arrives and nothing else changes:

1. `_ALGORITHM_PROFILES` (+ `_profile_aes` for key-size-aware AES) — algorithm
   vulnerability & susceptibility.
2. `_ASYM_RECOMMENDATION` / `_symmetric_recommendation` / `_PQ_PROFILES` —
   recommendations and NIST PQ names.

`profile_algorithm()` and `recommendation_for()` are the read-through points
used by the engine.

---

## 5. Editable business context

Analysts can override scanner metadata per asset without re-running the scan,
via `BusinessContext` (all fields optional):

```python
from app.risk_engine.types import AssetInput, BusinessContext
from app.risk_engine import evaluate_asset, default_config

ctx = BusinessContext(
    business_criticality="CRITICAL",
    data_lifetime_years=25,
    internet_exposure=True,
)
result = evaluate_asset(asset, config=default_config(), business_context=ctx)
```

Explicit context always wins over scanner values; unset fields fall through to
the asset. `risk_service.assess_scan(..., business_contexts={asset_id: ctx})`
applies this per asset in a scan.

---

## 6. Scale handling (0-100 → 0-10 contract)

The task spec's authoritative score is **0-100**; the team's contract
(`CryptoAsset.risk_score`, `RiskAssessment.risk_score`) is **0-10**
(`ge=0, le=10`). Resolution (per M1/M6 agreement): the engine always reasons in
0-100; `output.py` normalizes to 0-10 (`score_100 / 10`) only at the point of
writing the API payloads. The full 0-100 value is carried in
`factors.score_100` and the M6 rich view for full auditability.

---

## 7. M1 / M6 handoff (what Member 5 returns)

### 7.1 Triggering the engine (M5 runs, M1 hosts)

`risk_service.assess_scan(db, scan_id)` reads the scan's assets, runs the
engine, persists results, sets scan status to `RISK_ASSESSED`, and returns the
rich M6 views. A convenience endpoint is registered:

```
POST /risks/run?scan_id={scan_id}
```

### 7.2 Payloads Member 5 pushes (canonical schemas, unchanged)

Per asset, one `RiskAssessment` for `POST /risks/ingest?scan_id=...`:

```json
{
  "asset_id": "payment-tls-01",
  "risk_score": 10.0,
  "risk_level": "CRITICAL",
  "migration_priority": "URGENT",
  "mosca_assessment": "Harvest-now-decrypt-later: susceptible RSA protects data ...",
  "factors": {
    "score_100": 100.0,
    "priority_tier": 1,
    "algorithm": 80.0,
    "data_lifetime": 100.0,
    "business_criticality": 100.0,
    "internet_exposure": 100.0,
    "migration_complexity": 75.0,
    "mosca_boost": 12.0,
    "mosca_diagnostic": "harvest-now-decrypt-later",
    "harvest_now": true,
    "recommendation": "Replace RSA key exchange with ML-KEM (CRYSTALS-Kyber), e.g. ML-KEM-768."
  }
}
```

And one `Recommendation` per asset for `POST /recommendations/ingest?scan_id=...`:

```json
{
  "asset_id": "payment-tls-01",
  "recommendation": "Replace RSA key exchange with ML-KEM (CRYSTALS-Kyber), e.g. ML-KEM-768.",
  "explanation": "RSA key establishment is broken by Shor's algorithm; ML-KEM is the NIST-selected PQ KEM standardized in FIPS 203.",
  "suggested_target": "ML-KEM-768",
  "effort_estimate": "2-4 weeks"
}
```

The `recommendation` text is also written onto the asset's own
`recommendation` field (dashboard asset views read it there).

### 7.3 M6 consumption (unchanged stable APIs)

| Endpoint | Provides |
|---|---|
| `GET /risks/{scan_id}` | Per-asset rows: risk_score (0-10), level, priority, Mosca text |
| `GET /recommendations/{scan_id}` | Recommendation + target + explanation |
| `GET /assets?scan_id=...` | Assets incl. the five back-filled risk fields |
| `GET /scans/{scan_id}/summary` | Counts incl. `recommendation_count` |
| `GET /risks/run` response | Rich view: `breakdown`, `score_100`, `trade_offs`, `explanation`, `algorithm_known` |

A full worked example output for M6 is in
`docs/member5_m6_view_sample.json`.

---

## 8. Configuration

`RiskConfig` (all tunable, all validated):

| Field | Default | Notes |
|---|---|---|
| `weights` | algorithm .40 / lifetime .20 / criticality .15 / exposure .15 / complexity .10 | must sum to 1.0 |
| `thresholds` | LOW 25 / MEDIUM 50 / HIGH 75 / CRITICAL 101 | inclusive upper bound |
| `planning_horizon_years` | 20 | Mosca's `Z`; no invented date |
| `default_data_lifetime_years` | None | overrides missing-lifetime fallback |
| `migration_years` | LOW 1 / MEDIUM 3 / HIGH 5 | Mosca's `Y` |

---

## 9. Testing

Run from the repo root:

```bash
pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
```

Coverage: score boundaries (25/50/75/100), score scale & normalization,
determinism, weight transparency + validation, missing values (lifetime,
unknown algorithm, unknown key sizes), unknown-algorithm review path,
Mosca edge cases (X+Y=Z boundary, harvest-now triple condition, PQ-safe never
harvests, configurable horizon), business-context override, priority
escalation, recommendation contract (candidate+reason+trade-offs), DB service
integration (idempotent re-assessment, green/red coexistence, empty scan) and
a full HTTP pipeline test (M1 create scan → M3 ingest → M5 `/risks/run` → M6
reads).