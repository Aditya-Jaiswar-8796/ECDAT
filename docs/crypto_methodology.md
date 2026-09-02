# ECDAT Crypto Methodology

**Owned by:** Member 2 - Cryptography + PQC Technical Authority
**Project:** ECDAT SIH26164 - post-quantum crypto readiness tooling
**Documents:** modules/crypto_knowledge/{crypto_knowledge,methodology,recommendations}.json
**Date:** 2026-09-02

This document defines how ECDAT classifies cryptographic primitives, reasons
about post-quantum timelines, derives risk and drive migration. It is the
human-readable companion to the three machine-readable contracts shipped in
`modules/crypto_knowledge/`, which are the authoritative input for Members 5
(risk engine) and 6 (dashboard).

---

## 1. Deliverables index

| File | Content | Consumed by |
| --- | --- | --- |
| `modules/crypto_knowledge/crypto_knowledge.json` | Algorithm table (RSA, ECC, ECDSA, ECDH, AES, 3DES, DES, MD5, SHA-1, SHA-256, ML-KEM, ML-DSA), families, legacy scale, operations, extended lookups, fallback rules | M5, M6 |
| `modules/crypto_knowledge/methodology.json` | Mosca model, planning horizon, risk factors, scoring, thresholds, M3/M5 reviews, governance | M5 |
| `modules/crypto_knowledge/recommendations.json` | PQC purpose/migration role/trade-offs, hybrid migration, crypto-agility, per-algorithm actions | M5, M6 |
| `modules/crypto_knowledge/__init__.py` | Loader + deterministic resolution/scoring helpers | M5, M6 |
| `docs/crypto_methodology.md` | This document | all members |

---

## 2. Cryptographic categories

ECDAT reasons over six categories. Every scanner finding resolves to exactly
one effective primitive before risk is computed.

### 2.1 Hashing
One-way digests (SHA-256, SHA-1, MD5, SHA-3, BLAKE2). Used for integrity,
fingerprinting, MACs (HMAC) and KDF components. Quantum impact is limited to
Grover's quadratic speedup on preimages; the dominant threats to MD5 and
SHA-1 are *classical* collision attacks, so remediation is driven by
cryptanalysis, not by quantum forecasting.

### 2.2 Unauthenticated vs authenticated encryption
- **Symmetric encryption** (AES, 3DES, DES, Blowfish) - shared-secret bulk
  confidentiality. AES-256 is quantum-resilient; AES-128 loses ~half its
  security to Grover and should be raised to 256 where data must outlive a
  quantum era. 3DES/DES are classically broken.
- **Asymmetric encryption** (RSA-OAEP, hybrid envelopes) - public-key
  confidentiality, directly threatened by Shor's algorithm
  (harvest-now-decrypt-later).

### 2.3 Signatures
Authenticity/integrity/non-repudiation (ECDSA, RSA signatures, ML-DSA).
Quantum threat is two-fold: forgery of *new* signatures after key recovery,
and **retroactive forgery** of signatures issued before the transition. The
latter is captured by the `signature_longevity` risk factor.

### 2.4 Key establishment
Key exchange/KEM (ECDH, DH, ML-KEM). The most severe quantum surface:
adversaries can capture transcripts (TLS) or ciphertext today and decrypt
after the transition. Morse's number-one HNDL primitive.

### 2.5 Post-quantum cryptography (PQC)
NIST-standardised lattice primitives with no known quantum speed-up:
- **ML-KEM** (FIPS 203) - KEM; *purpose*: post-quantum key establishment;
  *migration role*: replaces ECDH/RSA key transport; *trade-offs*: larger
  keys/ciphertexts, constant-time implementation care, ongoing ecosystem
  adoption.
- **ML-DSA** (FIPS 204) - signatures; *migration role*: replaces ECDSA/RSA
  signatures; *trade-offs*: ~2.4-4.6 KB signatures (vs ~64-96 bytes ECDSA),
  different verification cost profile.
- **Hash-based signatures** (LMS/XMSS, FIPS 205) - niche complement for
  very-long-lived signed artifacts (statefulness must be managed).

### 2.6 Hybrid migration
Running the PQC primitive *alongside* the existing classical primitive so the
combination is secure if either is. See section 6.

### 2.7 Crypto-agility
The engineering discipline of being able to swap primitives, parameters and
providers without redesigns. See section 7.

---

## 3. Mosca-style reasoning

The Mosca problem states: a migration problem exists when

```
X (needed security lifetime) > Y (time to migrate) + Z (time until a
cryptanalytically relevant quantum computer)
```

ECDAT operationalises this as:

- **X = data_lifetime_years** - from the scan (`asset.data_lifetime_years`):
  how long confidentiality/integrity/signature-validity must hold.
- **Y = migration_time_years** - estimated from `asset.migration_complexity`
  via the configurable `migration_time_by_complexity` table
  (LOW ~0.5-1.5y, MEDIUM ~1.5-3y, HIGH ~3-5y).
- **Z = planning_horizon_years** - a **configurable parameter** (default 15,
  range 5-40) that stands in for the unknowable quantum-computer timeline.

### Hard rule: no invented quantum arrival dates

ECDAT never asserts when a quantum computer will exist. Z is always the
configured `planning_horizon_years` assumption, and the dashboard is required
to display the horizon in use so every label is interpretable. Sensitivity
analysis runs the model at multiple horizons (default/min/max) rather than a
single forecast. This keeps the tool defensible as engineering guidance.

### Exposure rule

An asset is exposed when:

```
data_lifetime_years > migration_time_years + planning_horizon_years
```

and the **harvest-now-decrypt-later (HNDL)** precondition applies (asymmetric
encryption or key establishment where an adversary can capture ciphertext or
agreement transcripts now). Exposure raises priority; it never sets a date.

---

## 4. Transparent risk-factor guidance

Member 5 populates `RiskAssessment.factors` using exactly the factor ids
below (defined in `methodology.json`). Weights are declared, not implicit:

| Factor id | Meaning | Applies to | Delta |
| --- | --- | --- | --- |
| `quantum_vulnerable_algorithm` | Shor-vulnerable asymmetric | encryption/KEM/signatures | 0.0 (in base) |
| `broken_classical_crypto` | Already broken classically | any | 0.0 (in base) |
| `harvest_now_decrypt_later` | Capturable today, decryptable later | asym. enc / KEM | +1.5 |
| `data_lifetime_exceeds_horizon` | X > Y + Z holds | enc / KEM / sig | +1.5 |
| `internet_exposure` | Internet-reachable, raises capture odds | enc / KEM / sig | +0.5 |
| `signature_longevity` | Signatures must verify for decades | signatures | +1.0 |

The first two are **reporting flags**: their impact is already inside
`base_risk_score`, so factoring them again would double-count. The last four
are contextual deltas on top of the base.

### Scoring pipeline (`methodology.json: risk_score_definition`)

1. Resolve the algorithm: exact -> alias -> extended -> fallback-by-operation
   (fallback always sets `review_required=true`).
2. Take `base_risk_score` from `crypto_knowledge.json`
   (e.g. RSA 7.0, AES 1.0, MD5/DES 10.0, ML-KEM/ML-DSA 0.0).
3. Apply the `key_size_adjustment` (nearest defined size): e.g. RSA-1024
   +2.0, AES-128 +1.0, P-256 0.0.
4. Add the factor deltas that are true.
5. Clamp to 0.0-10.0, round to one decimal.

### Level and priority mapping

- `risk_level`: LOW 0.0-3.9, MEDIUM 4.0-6.9, HIGH 7.0-8.9, CRITICAL 9.0-10.0.
- `migration_priority` base: LOW->LOW, MEDIUM->MEDIUM, HIGH->HIGH,
  CRITICAL->URGENT. Promotions: HNDL or horizon-exceeded promotes one tier
  (cap URGENT); classically-broken is at least HIGH.

---

## 5. Classification model

Every algorithm entry in `crypto_knowledge.json` carries:

- **family** - `asymmetric` / `symmetric` / `hash` / `pqc`
- **primitive/use** - resolved from `uses` + `m3_operation_mapping` to one of
  the canonical operations in `operations`.
- **quantum concern** - `severity` (NONE/LOW/MEDIUM/HIGH),
  `shor_vulnerable`, `grover_impact` and a plain-language `mechanism`.
- **legacy status** - `BROKEN` / `DEPRECATED` / `TRANSITIONAL` / `ACTIVE` /
  `PQC_RECOMMENDED`.
- **notes + references** - technical guidance and standards.

### Summary table

| Algorithm | Family | Legacy status | Quantum concern | Base score |
| --- | --- | --- | --- | --- |
| RSA | asymmetric | TRANSITIONAL | HIGH (Shor) | 7.0 |
| ECC | asymmetric | TRANSITIONAL | HIGH (Shor/ECDLP) | 7.0 |
| ECDSA | asymmetric | TRANSITIONAL | HIGH (Shor/ECDLP) | 7.0 |
| ECDH | asymmetric | TRANSITIONAL | HIGH (Shor/ECDLP) | 7.0 |
| AES | symmetric | ACTIVE | LOW (Grover; 256-bit OK) | 1.0 |
| 3DES | symmetric | BROKEN | LOW (classical dominates) | 9.0 |
| DES | symmetric | BROKEN | NONE (classical) | 10.0 |
| MD5 | hash | BROKEN | NONE (classical) | 10.0 |
| SHA-1 | hash | BROKEN | NONE (classical) | 9.5 |
| SHA-256 | hash | ACTIVE | LOW (Grover; 128-bit residual) | 1.0 |
| ML-KEM | pqc | PQC_RECOMMENDED | NONE | 0.0 |
| ML-DSA | pqc | PQC_RECOMMENDED | NONE | 0.0 |

Base scores assume typical sizes (RSA-2048, P-256, AES-256); M5 applies
key-size adjustments for deviations. Extended lookups cover the other
algorithms M3 emits (SHA-384/512, SHA-3, BLAKE2, HMAC, PBKDF2, scrypt,
bcrypt, argon2, Blowfish). Unknown/null algorithms are classified via
fallback rules keyed by operation with `review_required=true` so M5 never
fabricates a classification.

---

## 6. PQC migration and hybrid strategy

`recommendations.json` defines the target posture:

- **Key establishment**: ML-KEM-768 default (category 3); hybrid
  X25519+ML-KEM-768 while classical peers require it.
- **Signatures**: ML-DSA-65 default; dual ECDSA/RSA+ML-DSA certificates in
  transition; hash-based signatures (LMS/XMSS) for very-long-lived artifacts.
- **Hybrid rules**: use the PQC primitive *alongside* the classical one while
  classical is still trusted, so security holds if either component holds.
  Exit to pure PQC is a policy decision (remaining data lifetime shorter than
  the classical trust horizon, and all peers upgraded) - not a calendar date.
- **Trade-offs surfaced**: PQC key/ciphertext/signature sizes vs ECDSA/DH,
  verification cost profiles, constant-time implementation care, standards
  maturity and interop testing.

Per-algorithm actions (`per_algorithm`): RSA/ECC/ECDSA/ECDH REPLACE; AES
UPGRADE_PARAMETERS (256+GCM); 3DES/DES/MD5/SHA-1 REMOVE; SHA-256 KEEP;
ML-KEM/ML-DSA ADOPT.

---

## 7. Crypto-agility practices

- Inventory all primitives and parameters centrally (this project's assets +
  CBOM).
- Treat algorithm choice as configuration, never hard-coded literals.
- Use provider-native abstraction (JCA/JCE, OpenSSL providers, WebCrypto).
- Enforce a capability allow/deny policy and gate CI on it.
- Ship parameter upgrades as routine, reversible releases and keep key
  rotation/cert renewal ahead of schedule.
- Kill-switch legacy modes and measure usage telemetry for deprecation.
- Monitor crypto-relevant dependencies (CBOM, Member 4) for latest versions
  and CVEs; re-scan per release.

---

## 8. Review: Member 3 mappings

Review coordinated with Member 3 and captured in `methodology.json` ->
`review.m3_mapping_review`:

- `M3-01` (MEDIUM) - operation vocabulary inconsistent across detectors
  (`encryption` vs `symmetric_encryption`, `key_agreement` vs `keyexchange`,
  `hashing` vs `hash`). Resolved via `m3_operation_mapping`; M3 asked to
  normalise tokens.
- `M3-02` (LOW) - `DESede` covered by 3DES aliases; no scanner change.
- `M3-03` (MEDIUM) - no PQC detection in scanners; ML-KEM/ML-DSA requested in
  all detector known-algorithm lists.
- `M3-04` (MEDIUM) - `key_size` rarely populated; key-size adjustments starve
  without it. M3 to extract sizes from algorithm strings.
- `M3-05` (LOW) - bare `EC`/curve names resolve to ECC; primitive decided by
  operation.
- `M3-06` (LOW) - null algorithms handled by fallback rules
  (`review_required`).
- `M3-07` (LOW) - Java one-finding-per-line dedupe may drop a second
  primitive; documented limitation.

## 9. Review: Member 5 methodology

The M5 risk engine module does not exist yet in this repository. This review
defines the contract it must implement (`methodology.json` ->
`review.m5_methodology_review`):

- `M5-01` - M5 must fill `risk_score`, `risk_level`, `migration_priority`,
  `mosca_assessment` and `recommendation` from these files, and emit factor
  keys that match `risk_factors[].id`.
- `M5-02` (HIGH) - M5 must load the three JSON files as read-only reference
  data and never hard-code weights, thresholds or algorithm tables (risk of
  divergence).
- `M5-03` - keep the 0..10 clamp.
- `M5-04` - use `mosca_assessment_templates` and quote the planning horizon
  used, so the narrative is transparent.
- `M5-05` - `business_criticality` stays OUTSIDE the score formula (separate
  signal); it may inform ordering only.

---

## 10. Governance

- **Classification authority:** Member 2. All algorithms, families, legacy
  statuses, quantum severities, risk factors, weights, thresholds and
  template text are owned here.
- **Member 6 limits:** may *format, validate and render* the Member 2 JSON
  documents; must **not invent** classifications, weights, thresholds or
  algorithm entries. Any classification change flows through Member 2 and
  increments `schema_version`.
- **Change process:** update the three JSON files together, bump
  `schema_version`, extend the tests, update this document.
- **Configurable knobs:** `planning_horizon_years`, `migration_time_by_complexity`,
  `key_size_adjustments`, `risk_factors[].score_delta`, `risk_level_thresholds`.
- **Validation:** `python -m unittest tests.test_crypto_knowledge -v` - parses
  every JSON file, checks the required 12 algorithms, enum consistency,
  score/floor/threshold integrity, M3-operation fallback coverage and the
  no-invented-dates invariant.