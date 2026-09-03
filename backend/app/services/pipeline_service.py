"""Pipeline orchestrator.

Wires the uploaded ZIP through the actual analysis modules and into the DB.

This is what was missing: the upload endpoint merely staged the bundle and set
status to SCANNING — nothing ever extracted the archive, ran the source /
dependency / certificate scanners, or applied the risk engine. This service
runs the whole pipeline in a background thread so the API responds instantly
and the frontend watches progress via its existing polling.

Stages (matches the frontend stepper):
    Upload (done at HTTP layer)
      -> Discover:   extract + source scanner (parallel) -> crypto assets
      -> Analyze:    dependency scanner + certificate analyzer -> CBOM rows
      -> Risk:       risk engine -> risk fields + recommendations
      -> Complete:   status RISK_ASSESSED
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db import models
from app.db.database import SessionLocal
from app.schemas.certificate import Certificate
from app.schemas.crypto_asset import CryptoAssetCreate
from app.schemas.dependency import Dependency
from app.schemas.recommendation import Recommendation
from app.schemas.risk import RiskAssessment
from app.services import scan_service
from app.services.integration_service import (
    ingest_certificates,
    ingest_crypto_assets,
    ingest_dependencies,
    ingest_recommendations,
    ingest_risk_assessment,
)

# The analysis modules live at the repository root (sibling of backend/),
# so make sure that root is importable regardless of the launch working dir.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import the analysis modules lazily so a missing optional module never breaks
# the whole backend at import time — it just degrades that stage.
try:
    from modules.source_scanner.scanner import scan_directory
    _HAS_SOURCE_SCANNER = True
except Exception:  # pragma: no cover - defensive
    _HAS_SOURCE_SCANNER = False

try:
    from modules.dependency_scanner.scanner import scan_dependencies
    _HAS_DEP_SCANNER = True
except Exception:  # pragma: no cover - defensive
    _HAS_DEP_SCANNER = False

try:
    from modules.certificate_analyzer.analyzer import analyze_certificate_directory
    _HAS_CERT_ANALYZER = True
except Exception:  # pragma: no cover - defensive
    _HAS_CERT_ANALYZER = False

try:
    from modules.crypto_knowledge import base_score_for
    _HAS_KNOWLEDGE = True
except Exception:  # pragma: no cover - defensive
    _HAS_KNOWLEDGE = False

try:
    from app.risk_engine.engine import evaluate_asset
    from app.risk_engine.types import AssetInput
    from app.risk_engine.output import to_risk_assessment, to_recommendation
    _HAS_RISK_ENGINE = True
except Exception:  # pragma: no cover - defensive
    _HAS_RISK_ENGINE = False


# Supported manifest + certificate extensions the analyzers look for.
_MANIFEST_TYPES = ["package.json", "requirements.txt", "pom.xml"]
_CERT_EXTENSIONS = [".pem", ".crt", ".cer", ".cert", ".der"]


def _start_pipeline(scan_id: str) -> None:
    """Launch the pipeline for a scan on a daemon background thread.

    A fresh DB session is opened on the worker thread (SQLite connections are
    not shareable across threads). The thread is daemon so it never blocks
    server shutdown.
    """
    worker = threading.Thread(
        target=_run_pipeline_worker,
        args=(scan_id,),
        name=f"ecdat-pipeline-{scan_id}",
        daemon=True,
    )
    worker.start()


def _run_pipeline_worker(scan_id: str) -> None:
    """Run the full pipeline for one scan inside a worker thread."""
    db = SessionLocal()
    try:
        scan = scan_service.get_scan(db, scan_id)
        if scan is None:
            return

        scan_dir = scan_service.get_scan_dir(scan)
        # Locate the staged archive (persist_upload wrote it there).
        archive = _find_archive(scan_dir)
        if archive is None:
            scan_service.set_error(
                db, scan, "Staged bundle not found on disk; upload may have failed."
            )
            return

        extract_dir = scan_dir / "extracted"
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)
        extract_dir.mkdir(parents=True, exist_ok=True)

        # --- Discover: extract the archive safely, then scan source files ---
        try:
            with zipfile.ZipFile(archive) as zf:
                scan_service.safe_extract(zf, extract_dir)
        except Exception as exc:  # noqa: BLE001
            scan_service.set_error(db, scan, f"Extraction failed: {exc}")
            return

        _run_source_scan(db, scan_id, extract_dir)
        _run_dependency_scan(db, scan_id, extract_dir)
        _run_certificate_scan(db, scan_id, extract_dir)

        # --- Analyze complete: source + CBOM findings are persisted ---
        scan_service.set_status(db, scan, "SCAN_COMPLETE")

        # --- Risk: apply the deterministic risk engine + recommendations ---
        if _HAS_RISK_ENGINE:
            _run_risk_engine(db, scan_id)
            scan_service.set_status(db, scan, "RISK_ASSESSED")
        else:
            # Risk engine unavailable — still mark done but at SCAN_COMPLETE.
            pass
    except Exception as exc:  # noqa: BLE001
        import logging
        import traceback

        logging.getLogger("ecdat.pipeline").exception("Pipeline failed for %s", scan_id)
        scan = scan_service.get_scan(db, scan_id)
        if scan is not None:
            tb = traceback.format_exc(limit=6)
            scan_service.set_error(db, scan, f"Pipeline error: {exc}")
            logging.getLogger("ecdat.pipeline").error("Traceback:\n%s", tb)
    finally:
        db.close()


def _find_archive(scan_dir: Path) -> Optional[Path]:
    """Return the first .zip staged in the scan directory, if any."""
    if not scan_dir.exists():
        return None
    for item in scan_dir.iterdir():
        if item.is_file() and item.suffix.lower() == ".zip":
            return item
    return None


def _run_source_scan(db: Session, scan_id: str, root: Path) -> None:
    """Run the parallel source scanner and persist crypto asset findings."""
    if not _HAS_SOURCE_SCANNER:
        return
    result = scan_directory(str(root))
    findings: List[Dict[str, Any]] = result.get("findings", [])

    asset_payloads = []
    for f in findings:
        alg = (f.get("algorithm") or "UNKNOWN").strip() or "UNKNOWN"
        asset_payloads.append(
            {
                "id": _stable_id(f, alg),
                "algorithm": _normalize_algorithm_for_kb(alg),
                "operation": f.get("operation") or "unknown",
                "key_size": f.get("key_size"),
                "language": f.get("language") or "",
                "library": f.get("library"),
                "api": f.get("api"),
                "file_path": f.get("file_path") or "",
                "line_number": f.get("line_number"),
                "evidence": f.get("evidence"),
                "confidence": _confidence(f),
                # Scanner does not classify these; default conservative values
                # and let the risk engine / user refine later.
                "business_criticality": "MEDIUM",
                "data_lifetime_years": f.get("data_lifetime_years"),
                "internet_exposure": bool(f.get("internet_exposure")),
                "migration_complexity": f.get("migration_complexity") or "MEDIUM",
                "risk_score": None,
                "risk_level": None,
                "migration_priority": None,
                "mosca_assessment": None,
                "recommendation": None,
            }
        )

    if asset_payloads:
        ingest_crypto_assets(
            db, scan_id, [CryptoAssetCreate(**p) for p in asset_payloads]
        )


def _run_dependency_scan(db: Session, scan_id: str, root: Path) -> None:
    """Run the dependency scanner (recursively) and persist dependency rows."""
    if not _HAS_DEP_SCANNER:
        return
    # The dependency scanner only checks the root of a directory, so walk the
    # tree ourselves and invoke it per directory that holds a manifest.
    deps = _collect_dependencies(root)
    persisted = []
    for d in deps:
        rel = d.get("manifest_path", "")
        persisted.append(
            {
                "name": d.get("name", ""),
                "version": d.get("version"),
                "ecosystem": _ecosystem_for(d.get("manifest_type")),
                "crypto_relevant": bool(d.get("crypto_relevant", False)),
                "known_vulnerabilities": None,
                "latest_version": None,
            }
        )
    if persisted:
        ingest_dependencies(db, scan_id, [Dependency(**p) for p in persisted])


def _collect_dependencies(root: Path) -> List[Dict[str, Any]]:
    """Walk the extracted tree and run the dep scanner in each relevant dir."""
    from modules.dependency_scanner.scanner import scan_dependencies

    collected: List[Dict[str, Any]] = []
    for current, _dirs, files in os_walk(root):
        wanted = [
            f for f in files
            if f in ("package.json", "requirements.txt", "pom.xml")
        ]
        if not wanted:
            continue
        result = scan_dependencies(current)
        for dep in result.all_dependencies:
            rel = str(Path(dep.manifest_path).relative_to(root)).replace("\\", "/")
            collected.append(
                {
                    "name": dep.name,
                    "version": dep.version or "",
                    "manifest_path": rel,
                    "manifest_type": dep.manifest_type,
                    "crypto_relevant": bool(
                        dep.crypto_relevance and dep.crypto_relevance.is_relevant
                    ),
                }
            )
    return collected


def _run_certificate_scan(db: Session, scan_id: str, root: Path) -> None:
    """Analyze certificates recursively and persist them."""
    if not _HAS_CERT_ANALYZER:
        return
    certs = []
    for current, _dirs, files in os_walk(root):
        current = Path(current)
        pem_files = [
            f for f in sorted(files)
            if f.lower().endswith(tuple(_CERT_EXTENSIONS))
        ]
        for f in pem_files:
            certs.append((current, f))
    if not certs:
        return

    persisted = []
    for current, fname in certs:
        path = current / fname
        try:
            from modules.certificate_analyzer.analyzer import analyze_certificate_file
            finding = analyze_certificate_file(str(path))
        except Exception:  # noqa: BLE001
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        persisted.append(
            {
                "subject": getattr(finding, "subject", None),
                "issuer": getattr(finding, "issuer", None),
                "serial_number": getattr(finding, "serial_number", None),
                "fingerprint_sha256": getattr(finding, "fingerprint_sha256", None),
                "not_valid_before": getattr(finding, "not_before", None),
                "not_valid_after": getattr(finding, "not_after", None),
                "signature_algorithm": getattr(finding, "signature_algorithm", None),
                "key_algorithm": getattr(finding, "key_type", None),
                "key_size": getattr(finding, "key_size", None),
                "source_file": rel,
            }
        )
    if persisted:
        ingest_certificates(db, scan_id, [Certificate(**p) for p in persisted])


def _run_risk_engine(db: Session, scan_id: str) -> None:
    """Evaluate every ingested asset with the deterministic risk engine."""
    assets = (
        db.query(models.CryptoAssetModel)
        .filter(models.CryptoAssetModel.scan_id == scan_id)
        .all()
    )
    if not assets:
        return

    recommendations = []
    for asset in assets:
        inp = AssetInput(
            id=asset.id,
            algorithm=asset.algorithm,
            operation=asset.operation,
            key_size=_to_int(asset.key_size),
            business_criticality=asset.business_criticality or "MEDIUM",
            data_lifetime_years=_to_int(asset.data_lifetime_years),
            internet_exposure=bool(asset.internet_exposure),
            migration_complexity=asset.migration_complexity or "MEDIUM",
            confidence=asset.confidence or "MEDIUM",
            language=asset.language or "",
            file_path=asset.file_path or "",
        )
        assessment = evaluate_asset(inp)
        # Persist risk fields onto the asset row.
        ingest_risk_assessment(db, scan_id, to_risk_assessment(assessment))
        recommendations.append(to_recommendation(assessment))

    if recommendations:
        ingest_recommendations(db, scan_id, recommendations)


def _to_int(value) -> Optional[int]:
    """Coerce a possibly string-typed numeric field to int (or None)."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _stable_id(finding: Dict[str, Any], algorithm: str) -> str:
    """Derive a stable asset id from the file + line so re-scans dedupe."""
    import hashlib

    src = f"{finding.get('file_path', '')}:{finding.get('line_number', '')}:{algorithm}"
    return "asset-" + hashlib.sha1(src.encode("utf-8")).hexdigest()[:10]


def _confidence(finding: Dict[str, Any]) -> str:
    c = (finding.get("confidence") or "MEDIUM").upper()
    return c if c in {"LOW", "MEDIUM", "HIGH"} else "MEDIUM"


def _normalize_algorithm_for_kb(algorithm: str) -> str:
    """Map scanner outputs to a form the risk engine understands."""
    if not _HAS_KNOWLEDGE:
        return algorithm
    try:
        resolved = base_score_for(algorithm)
        return resolved.get("algorithm") or algorithm
    except Exception:  # noqa: BLE001
        return algorithm


def _ecosystem_for(manifest_type: Optional[str]) -> Optional[str]:
    return {
        "package.json": "npm",
        "requirements.txt": "pypi",
        "pom.xml": "maven",
    }.get(manifest_type)


def _os_walk(root: Path):
    """Small portable wrapper matching os.walk(dir) -> (dir, dirs, files)."""
    import os

    return os.walk(root)


# Alias so the helper reads consistently above.
os_walk = _os_walk
