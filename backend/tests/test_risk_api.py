"""API-level end-to-end test of the Member 5 risk pipeline.

Simulates the real team flows over the wire:
    M1: POST /scans                  (create the run)
    M3: POST /assets/ingest          (push crypto findings)
    M5: POST /risks/run              (run the deterministic engine)
    M6: GET /risks/{scan_id},
        GET /recommendations/{scan_id},
        GET /scans/{scan_id}/summary (dashboard consumption)
"""

import os
import tempfile

# Point the app at an isolated temp DB *before* importing the app so the
# module-level engine binds to it (stays clean for the rest of the suite).
os.environ["ECDAT_DB_PATH"] = os.path.join(
    tempfile.gettempdir(), f"ecdat_test_api_{os.getpid()}.db"
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_full_risk_pipeline_over_api():
    with TestClient(app) as client:
        # --- M1: create a scan ---
        resp = client.post("/scans", json={"name": "payments", "language": "java"})
        assert resp.status_code == 201
        scan_id = resp.json()["scan_id"]

        # --- M3: ingest canonical crypto assets (risk fields null) ---
        assets = [
            {
                "id": "a-rsa",
                "algorithm": "RSA",
                "operation": "keyexchange",
                "key_size": 2048,
                "language": "java",
                "file_path": "src/TlsBootstrap.java",
                "business_criticality": "CRITICAL",
                "data_lifetime_years": 25,
                "internet_exposure": True,
                "migration_complexity": "HIGH",
                "confidence": "HIGH",
            },
            {
                "id": "a-aes",
                "algorithm": "AES",
                "operation": "encryption",
                "key_size": 256,
                "language": "java",
                "file_path": "src/CipherUtil.java",
                "business_criticality": "CRITICAL",
                "data_lifetime_years": 25,
                "internet_exposure": True,
                "migration_complexity": "LOW",
                "confidence": "HIGH",
            },
        ]
        resp = client.post(f"/assets/ingest?scan_id={scan_id}", json=assets)
        assert resp.status_code == 201, resp.text

        # --- M5: run the deterministic risk engine ---
        resp = client.post(f"/risks/run?scan_id={scan_id}")
        assert resp.status_code == 200, resp.text
        views = resp.json()
        assert len(views) == 2

        by_id = {v["asset_id"]: v for v in views}
        # RSA-2048, long-lived, exposed => top of the risk spectrum.
        assert by_id["a-rsa"]["risk_level"] == "CRITICAL"
        assert by_id["a-rsa"]["migration_priority"] == "URGENT"
        assert by_id["a-rsa"]["harvest_now"] is True
        assert by_id["a-rsa"]["score_100"] > by_id["a-aes"]["score_100"]
        # AES-256 stays green even in hostile context.
        assert by_id["a-aes"]["risk_level"] == "LOW"

        # --- M6: read assessmet rows ---
        resp = client.get(f"/risks/{scan_id}")
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["assessed_count"] == 2
        scores = {a["asset_id"]: a["risk_score"] for a in summary["assessments"]}
        assert scores["a-rsa"] <= 10  # contract is 0-10 at the API.

        # --- M6: read recommendations ---
        resp = client.get(f"/recommendations/{scan_id}")
        assert resp.status_code == 200
        recs = {r["asset_id"]: r for r in resp.json()}
        assert "ML-KEM" in recs["a-rsa"]["suggested_target"]
        assert recs["a-rsa"]["recommendation"]
        assert recs["a-rsa"]["explanation"]

        # --- M6: scan summary counts both ---
        resp = client.get(f"/scans/{scan_id}/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["asset_count"] == 2
        assert body["recommendation_count"] == 2


def test_risk_run_requires_existing_scan():
    with TestClient(app) as client:
        resp = client.post("/risks/run?scan_id=does-not-exist")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]