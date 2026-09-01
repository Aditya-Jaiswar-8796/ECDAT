"""Unified dependency scanner - orchestrates all manifest parsers.

Provides a single entry point to scan multiple manifest types
and produce a unified list of dependency findings.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from .package_json import parse_package_json, DependencyFinding, ParseResult
from .requirements_txt import (
    parse_requirements_txt,
    DependencyFinding as ReqDependencyFinding,
    ParseResult as ReqParseResult,
)
from .pom_xml import (
    parse_pom_xml,
    DependencyFinding as PomDependencyFinding,
    ParseResult as PomParseResult,
)


@dataclass
class ScanResult:
    """Aggregated result from scanning all manifest types."""
    target_path: str
    all_dependencies: List[DependencyFinding] = field(default_factory=list)
    manifest_results: List[ParseResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_dependencies: int = 0
    crypto_relevant_count: int = 0


def scan_dependencies(
    target_path: str,
    check_crypto: bool = True,
    manifest_types: Optional[List[str]] = None,
) -> ScanResult:
    """Scan a directory or single file for dependency manifests.

    Automatically detects and parses:
    - package.json
    - requirements.txt
    - pom.xml

    Args:
        target_path: Path to a directory to scan or a single manifest file.
        check_crypto: Whether to evaluate cryptographic relevance.
        manifest_types: Optional filter for which manifest types to scan.
                        If None, scans all supported types.

    Returns:
        ScanResult with all discovered dependencies and metadata.
    """
    result = ScanResult(target_path=target_path)

    # Determine files to scan
    files_to_scan = _discover_manifests(target_path, manifest_types)

    if not files_to_scan:
        result.errors.append(f"No supported manifest files found in: {target_path}")
        return result

    for file_path, manifest_type in files_to_scan:
        parse_result = _parse_manifest(file_path, manifest_type, check_crypto)
        result.manifest_results.append(parse_result)

        # Convert dependency findings to unified type and collect
        for dep in parse_result.dependencies:
            unified = DependencyFinding(
                name=dep.name,
                version=dep.version,
                manifest_path=dep.manifest_path,
                manifest_type=dep.manifest_type,
                section=dep.section,
                crypto_relevance=dep.crypto_relevance,
                raw_entry=dep.raw_entry,
                parse_errors=dep.parse_errors,
            )
            result.all_dependencies.append(unified)
            result.total_dependencies += 1
            if dep.crypto_relevance and dep.crypto_relevance.is_relevant:
                result.crypto_relevant_count += 1

        # Collect any parse errors
        if not parse_result.success:
            result.errors.extend(parse_result.errors)

    return result


def _discover_manifests(
    target_path: str,
    manifest_types: Optional[List[str]] = None,
) -> List[tuple]:
    """Discover manifest files in the given path.

    Returns list of (file_path, manifest_type) tuples.
    """
    discovered = []

    # Supported manifest filenames mapped to their parser type
    known_manifests = {
        "package.json": "package.json",
        "requirements.txt": "requirements.txt",
        "pom.xml": "pom.xml",
    }

    # Filter by requested types if specified
    if manifest_types:
        known_manifests = {
            k: v for k, v in known_manifests.items()
            if v in manifest_types
        }

    if os.path.isfile(target_path):
        # Single file - check if it's a known manifest
        basename = os.path.basename(target_path)
        if basename in known_manifests:
            discovered.append((target_path, known_manifests[basename]))
        else:
            # Try to guess type from extension/content
            manifest_type = _guess_manifest_type(target_path)
            if manifest_type:
                discovered.append((target_path, manifest_type))
    elif os.path.isdir(target_path):
        # Scan directory for known manifest files
        for filename, manifest_type in known_manifests.items():
            file_path = os.path.join(target_path, filename)
            if os.path.isfile(file_path):
                discovered.append((file_path, manifest_type))
    else:
        # Path doesn't exist - will be handled by individual parsers
        for filename, manifest_type in known_manifests.items():
            file_path = os.path.join(target_path, filename)
            discovered.append((file_path, manifest_type))

    return discovered


def _guess_manifest_type(file_path: str) -> Optional[str]:
    """Guess the manifest type from file extension or content hints."""
    basename = os.path.basename(file_path).lower()
    if basename == "package.json":
        return "package.json"
    if basename in ("requirements.txt", "requirements.in", "requirements-lock.txt"):
        return "requirements.txt"
    if basename == "pom.xml":
        return "pom.xml"
    return None


def _parse_manifest(
    file_path: str,
    manifest_type: str,
    check_crypto: bool,
) -> ParseResult:
    """Route to the correct parser for the given manifest type."""
    if manifest_type == "package.json":
        return parse_package_json(file_path, check_crypto=check_crypto)
    elif manifest_type == "requirements.txt":
        return parse_requirements_txt(file_path, check_crypto=check_crypto)
    elif manifest_type == "pom.xml":
        return parse_pom_xml(file_path, check_crypto=check_crypto)
    else:
        result = ParseResult(manifest_path=file_path, manifest_type=manifest_type)
        result.success = False
        result.errors.append(f"Unsupported manifest type: {manifest_type}")
        return result
