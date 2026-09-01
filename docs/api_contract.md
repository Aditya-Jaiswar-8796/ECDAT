# ECDAT API Contract

Central persistence + integration layer for the ECDAT post-quantum readiness
tooling (SIH 26164). Owned by **Member 1** (Tech Lead, FastAPI + SQLite +
Integration).

Base URL (local dev): `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs` (OpenAPI/Swagger).

---

## 1. Canonical CryptoAsset schema (single source of truth)

The `CryptoAsset` payload below is the **only** cross-team contract for crypto
findings. It is defined once in `backend/app/schemas/crypto_asset.py` and is
used by Members 3, 4, 5 and 6. **Do not re-define it elsewhere.**

```json
{
  "id": "asset-001",
  "algorithm": "RSA",
  "operation": "encryption",
  "key_size": 2048,
  "language": "java",
  "library": "javax.crypto",
  "api": "Cipher.getInstance",
  "file_path": "src/PaymentService.java",
  "line_number": 42,
  "evidence": "Cipher.getInstance(\"RSA/ECB/OAEPWithSHA-256AndMGF1Padding\")",
  "confidence": "HIGH",
  "business_criticality": "CRITICAL",
  "data_lifetime_years": 10,
  "internet_exposure": true,
  "migration_complexity": "HIGH",
  "risk_score": null,
  "risk_level": null,
  "migration_priority": null,
  "mosca_assessment": null,
  "recommendation": null
}
```

| Field | Type | Enums / notes | Populated by |
|---|---|---|---|
| `id` | string | Scanner-assigned stable id | M3 |
| `algorithm` | string | e.g. `RSA`, `AES`, `ECDSA`, `SHA256` | M3 |
| `operation` | string | e.g. `encryption`, `signing`, `hash`, `keyexchange` | M3 |
| `key_size` | int? | | M3 |
| `language` | string | e.g. `java`, `python`, `csharp` | M3 |
| `library` | string? | e.g. `javax.crypto`, `bouncycastle` | M3 |
| `api` | string? | e.g. `Cipher.getInstance`, `ECDH.derive` | M3 |
| `file_path` | string | Path within the source tree | M3 |
| `line_number` | int? | | M3 |
| `evidence` | string? | Matched source snippet | M3 |
| `confidence` | enum | `LOW` \| `MEDIUM` \| `HIGH` | M3 |
| `business_criticality` | enum | `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` | M3 |
| `data_lifetime_years` | int? | Expected data retention years | M3 |
| `internet_exposure` | bool | Defaults `false` | M3 |
| `migration_complexity` | enum | `LOW` \| `MEDIUM` \| `HIGH` | M3 |
| `risk_score` | float? | 0..10 | M5 |
| `risk_level` | string? | `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` | M5 |
| `migration_priority` | string? | `LOW` \| `MEDIUM` \| `HIGH` \| `URGENT` | M5 |
| `mosca_assessment` | string? | Qualitative MOSAIC note | M5 |
| `recommendation` | string? | Suggested remediation | M5 |

The five risk fields start `null` and are back-filled by Member 5.

---

## 2. Endpoints

### 2.1 Metadata

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service banner |
| GET | `/health` | Liveness + DB connectivity check |

`GET /health` →
```json
{ "status": "ok", "database": "up" }
```

### 2.2 Scans + upload (M4/M6 visibility)

| Method | Path | Description |
|---|---|---|
| POST | `/scans` | Create a scan → `201`, body `ScanCreate` |
| POST | `/scans/{scan_id}/upload` | Upload a ZIP project bundle (multipart, field `upload`) |
| GET | `/scans` | List scans (newest first) |
| GET | `/scans/{scan_id}` | Single scan |
| GET | `/scans/{scan_id}/summary` | Aggregate finding counts |

`POST /scans` body:
```json
{ "name": "payment-gateway", "project_name": "pgw", "language": "java" }
```
Response `Scan`:
```json
{
  "name": "payment-gateway",
  "project_name": "pgw",
  "language": "java",
  "scan_id": "scan-1a2b3c4d",
  "status": "RECEIVED",
  "created_at": "2026-09-01T10:00:00Z",
  "updated_at": "2026-09-01T10:00:00Z",
  "error": null,
  "asset_count": 0,
  "dependency_count": 0,
  "certificate_count": 0
}
```

**Upload rules (security):**
- Only `.zip` archives are accepted (anything else → `415`).
- Max upload size is 100 MB (`413` if exceeded).
- The archive is validated as a well-formed ZIP; corrupt archives → `400`.
- Source code is **never executed**; it is only stored for M3 parsing.
- Extraction (if needed later) rejects `..`/absolute-path members (path
  traversal protection in `scan_service.safe_extract`).

`GET /scans/{scan_id}/summary` →
```json
{
  "asset_count": 3,
  "dependency_count": 12,
  "certificate_count": 2,
  "recommendation_count": 1
}
```

### 2.3 Assets (M3 writes, M6 reads)

| Method | Path | Description |
|---|---|---|
| POST | `/assets/ingest?scan_id={id}` | Bulk create assets for a scan → `201` |
| GET | `/assets` | List assets (filter `?scan_id=`) |
| GET | `/assets/{asset_pk}` | One asset (DB primary key) |
| PATCH | `/assets/{asset_pk}` | Partial update (M5 risk fields, M6 edits) |
| DELETE | `/assets/{asset_pk}` | Delete an asset → `204` |

`POST /assets/ingest?scan_id=scan-1a2b3c4d` body: array of canonical
`CryptoAsset` (without the five risk fields or `null`). Re-ingesting the same
scan replaces prior assets (idempotent re-scans).

### 2.4 Risks (M5 writes, M6 reads)

| Method | Path | Description |
|---|---|---|
| POST | `/risks/ingest?scan_id={id}` | Ingest one risk assessment → `204` |
| GET | `/risks` | List assessed assets (filter `?scan_id=`) |
| GET | `/risks/{scan_id}` | Per-scan risk summary |

`POST /risks/ingest?scan_id=...` body (`RiskAssessment`):
```json
{
  "asset_id": "asset-001",
  "risk_score": 8.5,
  "risk_level": "HIGH",
  "migration_priority": "HIGH",
  "mosca_assessment": "RSA-2048 harvest-now-decrypt-later risk",
  "factors": { "harvest_now_decrypt_later": true }
}
```
When `asset_id` is omitted, the assessment is applied to **all** assets of the
scan.

### 2.5 Recommendations (M5 writes, M6 reads)

| Method | Path | Description |
|---|---|---|
| POST | `/recommendations/ingest?scan_id={id}` | Ingest recommendations → `204` |
| GET | `/recommendations` | List (filter `?scan_id=`) |
| GET | `/recommendations/{scan_id}` | Recommendations for one scan |

Body (`list[Recommendation]`):
```json
[
  {
    "asset_id": "asset-001",
    "recommendation": "Migrate RSA-2048 to ML-KEM for key exchange",
    "explanation": "RSA-2048 is vulnerable to Harvest-Now-Decrypt-Later ...",
    "suggested_target": "ML-KEM-768",
    "effort_estimate": "2-4 weeks"
  }
]
```

### 2.6 CBOM (M4 writes, M6 reads)

| Method | Path | Description |
|---|---|---|
| POST | `/cbom/dependencies/ingest?scan_id={id}` | Ingest dependencies → `204` |
| POST | `/cbom/certificates/ingest?scan_id={id}` | Ingest certificates → `204` |
| GET | `/cbom/{scan_id}/dependencies` | Dependencies for a scan |
| GET | `/cbom/{scan_id}/certificates` | Certificates for a scan |
| GET | `/cbom/{scan_id}` | Combined CBOM view |

Dependency (`list[Dependency]`):
```json
[
  {
    "name": "bouncycastle",
    "version": "1.70",
    "ecosystem": "maven",
    "crypto_relevant": true,
    "known_vulnerabilities": "CVE-2023-1234",
    "latest_version": "1.78"
  }
]
```

Certificate (`list[Certificate]`):
```json
[
  {
    "subject": "CN=api.example.com",
    "issuer": "CN=RootCA",
    "serial_number": "01:AB:...",
    "fingerprint_sha256": "e3b0c442...",
    "not_valid_before": "2020-01-01",
    "not_valid_after": "2026-01-01",
    "signature_algorithm": "RSASSA-PKCS1-v1_5",
    "key_algorithm": "RSA",
    "key_size": 2048,
    "source_file": "keystore.jks"
  }
]
```

---

## 3. Error responses

All routes return FastAPI's standard error shape on failure:

```json
{ "detail": "Scan 'scan-xyz' not found" }
```

| Code | Meaning |
|---|---|
| 400 | Invalid payload / corrupt archive / illegal archive path |
| 404 | Scan or asset does not exist |
| 413 | Upload exceeds size limit |
| 415 | Unsupported upload type (not `.zip`) |
| 422 | Request validation error (FastAPI default) |

---

## 4. Change management

- The canonical `CryptoAsset` is defined in
  `backend/app/schemas/crypto_asset.py`. Any change must be coordinated with
  M3, M4, M5 and M6 and reflected in this document.
- New ingest endpoints always follow the pattern
  `POST /<area>/ingest?scan_id={id}` with the canonical schema as the body.