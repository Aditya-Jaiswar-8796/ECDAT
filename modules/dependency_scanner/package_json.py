"""Package.json dependency manifest parser.

Extracts dependencies from Node.js package.json files and evaluates
their cryptographic relevance. Handles malformed JSON and missing files safely.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .crypto_relevance import CryptoRelevance, check_crypto_relevance


@dataclass
class DependencyFinding:
    """A single dependency discovered in a manifest file."""
    name: str
    version: str
    manifest_path: str
    manifest_type: str
    section: str  # "dependencies", "devDependencies", "peerDependencies", etc.
    crypto_relevance: Optional[CryptoRelevance] = None
    raw_entry: Optional[str] = None  # original entry for traceability
    parse_errors: List[str] = field(default_factory=list)


@dataclass
class ParseResult:
    """Result of parsing a single manifest file."""
    manifest_path: str
    manifest_type: str
    dependencies: List[DependencyFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    success: bool = True


def parse_package_json(file_path: str, check_crypto: bool = True) -> ParseResult:
    """Parse a package.json file and extract all dependency sections.

    Extracts dependencies from: dependencies, devDependencies,
    peerDependencies, optionalDependencies, and bundleDependencies.

    Args:
        file_path: Path to the package.json file.
        check_crypto: Whether to evaluate cryptographic relevance.

    Returns:
        ParseResult with discovered dependencies and any errors encountered.
    """
    result = ParseResult(
        manifest_path=file_path,
        manifest_type="package.json",
    )

    # Handle missing file
    if not os.path.exists(file_path):
        result.success = False
        result.errors.append(f"File not found: {file_path}")
        return result

    # Read and parse JSON
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError) as e:
        result.success = False
        result.errors.append(f"Failed to read file: {e}")
        return result

    if not content.strip():
        result.success = False
        result.errors.append("File is empty")
        return result

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        result.success = False
        result.errors.append(f"Invalid JSON: {e}")
        return result

    if not isinstance(data, dict):
        result.success = False
        result.errors.append("package.json root is not a JSON object")
        return result

    # Dependency section names to scan
    dep_sections = [
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
        "bundleDependencies",
    ]

    for section in dep_sections:
        section_data = data.get(section)
        if section_data is None:
            continue
        if not isinstance(section_data, dict):
            result.errors.append(f"Section '{section}' is not a JSON object - skipped")
            continue

        for dep_name, version_spec in section_data.items():
            version_str = _normalize_version(version_spec)
            finding = DependencyFinding(
                name=dep_name,
                version=version_str,
                manifest_path=file_path,
                manifest_type="package.json",
                section=section,
                raw_entry=f'"{dep_name}": "{version_spec}"',
            )

            # Evaluate cryptographic relevance if requested
            if check_crypto:
                finding.crypto_relevance = check_crypto_relevance(dep_name)

            result.dependencies.append(finding)

    return result


def _normalize_version(version_spec: object) -> str:
    """Normalize a package.json version specifier to a readable string.

    Handles version strings, git URLs, local paths, and other formats.
    """
    if isinstance(version_spec, str):
        return version_spec.strip()
    if isinstance(version_spec, dict):
        # Could be a complex specifier like {"version": "1.0.0", "optional": true}
        if "version" in version_spec:
            return str(version_spec["version"])
        return str(version_spec)
    return str(version_spec) if version_spec else "*"
