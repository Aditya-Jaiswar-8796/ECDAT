from __future__ import annotations

import os
from typing import Any, Dict, List

from concurrent.futures import ThreadPoolExecutor, as_completed

from . import file_discovery
from .evidence import read_source_lines
from .detectors import java, javascript, python

LANGUAGE_DETECTORS: Dict[str, Any] = {
    "java": java,
    "python": python,
    "javascript": javascript,
    "typescript": javascript,
}

# Concurrency knob: files are scanned in parallel rather than one at a time.
MAX_WORKERS = int(os.getenv("ECDAT_SCAN_WORKERS", "8"))


def scan_file(file_path: str) -> List[Dict[str, Any]]:
    language = file_discovery.detect_language(file_path)
    if language is None:
        return []

    detector = LANGUAGE_DETECTORS.get(language)
    if detector is None:
        return []

    lines = read_source_lines(file_path)
    if not lines:
        return []

    return detector.detect(file_path, lines)


def _scan_one(file_path: str):
    try:
        return file_path, scan_file(file_path), None
    except Exception as exc:  # noqa: BLE001 - scanner must never crash on one file
        return file_path, [], str(exc)


def scan_directory(root_dir: str) -> Dict[str, Any]:
    source_files = file_discovery.discover_source_files(root_dir)

    if not source_files:
        return {
            "scan_root": os.path.normpath(root_dir).replace("\\", "/"),
            "files_scanned": 0,
            "total_findings": 0,
            "errors": [],
            "findings": [],
        }

    all_findings: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    # Scan supported files in parallel. worker count is capped by config; each
    # task is independent so results merge in completion order.
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(source_files)))) as pool:
        futures = {pool.submit(_scan_one, fp): fp for fp in source_files}
        for future in as_completed(futures):
            file_path, findings, err = future.result()
            if err is not None:
                errors.append({"file_path": file_path, "error": err})
            else:
                all_findings.extend(findings)

    return {
        "scan_root": os.path.normpath(root_dir).replace("\\", "/"),
        "files_scanned": len(source_files),
        "total_findings": len(all_findings),
        "errors": errors,
        "findings": all_findings,
    }


def scan(root: str) -> Dict[str, Any]:
    if os.path.isfile(root):
        findings = scan_file(root)
        return {
            "scan_root": os.path.normpath(root).replace("\\", "/"),
            "files_scanned": 1,
            "total_findings": len(findings),
            "errors": [],
            "findings": findings,
        }
    return scan_directory(root)