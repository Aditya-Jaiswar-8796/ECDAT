from __future__ import annotations

import os
from typing import Any, Dict, List

from . import file_discovery
from .evidence import read_source_lines
from .detectors import java, javascript, python

LANGUAGE_DETECTORS: Dict[str, Any] = {
    "java": java,
    "python": python,
    "javascript": javascript,
    "typescript": javascript,
}


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


def scan_directory(root_dir: str) -> Dict[str, Any]:
    source_files = file_discovery.discover_source_files(root_dir)

    all_findings: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for file_path in source_files:
        try:
            findings = scan_file(file_path)
            all_findings.extend(findings)
        except Exception as exc:
            errors.append({"file_path": file_path, "error": str(exc)})

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