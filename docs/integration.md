# ECDAT Integration Guide

Integration design for the ECDAT team (SIH 26164). Owned by **Member 1**
(Tech Lead). This document defines how members push/pull results through the
backend and what contracts each member must respect.

## 1. Pipeline flow

```
                    Member 1 backend (SQLite store + API)
 M3 ── source scan ──► /assets/ingest ─────────┐
 M4 ── deps + certs ─► /cbom/.../ingest ───────┤
 M4 ── CBOM          ─► /cbom/{id} (read)      ├──► M5 risk engine ──► /risks/ingest
                                              │                        + /recommendations/ingest
 M6 ── dashboard ◄── /assets, /risks,          │
                      /recommendations, /cbom, /
                      /scans/{id}/summary      /
                            (stable REST API) /
```

Simplified: **M3 + M4 → M1 → M5 → M1 API → M6**

## 2. Handoff contract by member

### Member 3 (source scanner)
- Finds cryptographic primitives in the uploaded source tree.
- Produces a **list of canonical `CryptoAsset`** objects (see
  `docs/api_contract.md` §1). Risk fields (`risk_score` … `recommendation`)
  are sent as `null`.
- **Push to Member 1:** `POST /assets/ingest?scan_id={scan_id}` with a JSON
  array of assets. Response `201` with the persisted canonical assets.
- Re-ingesting the same `scan_id` **replaces** the previous asset set, so
  re-runs are safe.
- Reads the staged bundle from disk (see §4) — the bundle is **not** parsed by
  Member 1.

### Member 4 (dependencies / certificates / CBOM)
- Scans the bundle for third-party libraries and X.509 certificates/keystores.
- **Push dependencies:** `POST /cbom/dependencies/ingest?scan_id={scan_id}`
  with `list[Dependency]` (see §2.6 of the API contract).
- **Push certificates:** `POST /cbom/certificates/ingest?scan_id={scan_id}`
  with `list[Certificate]`.
- **Read the combined CBOM for the dashboard:**
  `GET /cbom/{scan_id}` (or `/dependencies`, `/certificates` separately).
- Re-ingesting replaces prior rows for the scan (idempotent).

### Member 5 (risk engine)
- Consumes the persisted assets, dependencies and certificates from the stable
  APIs (`GET /assets?scan_id=`, `GET /cbom/{scan_id}`).
- Computes `risk_score`, `risk_level`, `migration_priority`,
  `mosca_assessment`, plus a `recommendation` + `explanation`.
- **Push results back:**
  - `POST /risks/ingest?scan_id={scan_id}` with one `RiskAssessment`.
    Per-asset: set `asset_id`; scan-wide: omit `asset_id`.
  - `POST /recommendations/ingest?scan_id={scan_id}` with `list[Recommendation]`.
- The assessment overwrites the null risk fields on the matching asset(s);
  recommendations are stored separately.
- A convenience: `PATCH /assets/{asset_pk}` also accepts the five risk fields
  + recommendation directly on an asset if M5 prefers per-asset updates.

### Member 6 (dashboard/frontend)
- Reads everything from the stable APIs. Do **not** hit internal sqlite.
- Endpoints used: `GET /scans`, `GET /scans/{id}/summary`,
  `GET /assets?scan_id=`, `GET /risks/{scan_id}`, `GET /recommendations/{scan_id}`,
  `GET /cbom/{scan_id}`.
- Creates new runs via `POST /scans` + `POST /scans/{id}/upload`.

## 3. Stable API guarantees (Member 1 promiss)

1. Response shapes are versioned through OpenAPI (`/docs`); breaking changes
   are coordinated and documented in `docs/api_contract.md`.
2. All writes are idempotent per `scan_id` (re-push replaces prior findings).
3. Errors are explicit, structured FastAPI errors (`{ "detail": "..." }`).
4. No source code from uploads is ever executed by the backend.

## 4. Upload / staging

- `POST /scans` returns `scan_id`.
- `POST /scans/{scan_id}/upload` stores the archive under
  `backend/uploads/{scan_id}/` (root configurable via `ECDAT_UPLOAD_DIR`).
- Member 3 reads the bundle from that directory (or from the returned scan
  object) directly. Only `.zip` is accepted (100 MB cap).
- Member 1 provides `safe_extract` in
  `backend/app/services/scan_service.py` for anyone that needs to expand the
  bundle with path-traversal protection.

## 5. Local run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # PowerShell (Windows)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verify: `GET http://localhost:8000/health` → `{"status":"ok","database":"up"}`.

## 6. Working example (curl)

```bash
# 1. Create a scan
curl -X POST http://localhost:8000/scans -H "Content-Type: application/json" \
  -d '{"name":"demo","language":"java"}'

# 2. Upload source bundle
curl -X POST http://localhost:8000/scans/scan-1a2b3c4d/upload -F "upload=@project.zip"

# 3. M3 pushes assets
curl -X POST "http://localhost:8000/assets/ingest?scan_id=scan-1a2b3c4d" \
  -H "Content-Type: application/json" -d '[{"id":"asset-001", ...canonical asset...}]'

# 4. M5 pushes risk + recommendation
curl -X POST "http://localhost:8000/risks/ingest?scan_id=scan-1a2b3c4d" \
  -H "Content-Type: application/json" \
  -d '{"asset_id":"asset-001","risk_score":8.5,"risk_level":"HIGH","migration_priority":"HIGH"}'

# 5. M6 renders the dashboard
curl http://localhost:8000/scans/scan-1a2b3c4d/summary
curl http://localhost:8000/assets?scan_id=scan-1a2b3c4d
```

## 7. Open questions for the team

1. **Asset id uniqueness** — does M3 guarantee `id` is unique within a scan
   (or globally)? Currently the store keys assets by DB primary key and keeps
   `id` as the scanner-supplied identifier; M5 addresses assets by `id`.
2. **ZIP structure** — confirm the bundle layout M3 expects (repo root inside
   the zip, or the zip root itself is the repo root).
3. **Risk scope for M5** — should `POST /risks/ingest` be per-asset (current)
   or should M5 prefer pushing the full list of assessed assets at once?
4. **CBOM "output path"** — Member 4 also produces CBOM artifacts; confirm
   whether they are pushed via API only or also written to disk (and if so,
   where).
5. **recommendation field duplication** — M5 can put the recommendation both
   in the asset (`recommendation`) and in `/recommendations`. Confirm the
   dashboard consumes only one canonical source.