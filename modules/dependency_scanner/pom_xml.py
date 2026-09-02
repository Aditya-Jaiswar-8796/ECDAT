"""Maven pom.xml dependency manifest parser.

Extracts dependencies from Java/Maven pom.xml files and evaluates
their cryptographic relevance. Handles malformed XML, missing files,
and missing elements safely.

Uses only Python standard library XML parsing (xml.etree.ElementTree).
"""

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .crypto_relevance import CryptoRelevance, check_crypto_relevance


# Maven namespace used in pom.xml files
_MAVEN_NS = "{http://maven.apache.org/POM/4.0.0}"


@dataclass
class DependencyFinding:
    """A single dependency discovered in a pom.xml file."""
    name: str
    version: str
    manifest_path: str
    manifest_type: str
    section: str  # "compile", "test", "provided", "runtime", "system"
    group_id: Optional[str] = None
    artifact_id: Optional[str] = None
    scope: Optional[str] = None
    crypto_relevance: Optional[CryptoRelevance] = None
    raw_entry: Optional[str] = None
    parse_errors: List[str] = field(default_factory=list)


@dataclass
class ParseResult:
    """Result of parsing a pom.xml file."""
    manifest_path: str
    manifest_type: str
    dependencies: List[DependencyFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    success: bool = True
    project_group_id: Optional[str] = None
    project_artifact_id: Optional[str] = None
    project_version: Optional[str] = None


def parse_pom_xml(file_path: str, check_crypto: bool = True) -> ParseResult:
    """Parse a Maven pom.xml file and extract all dependencies.

    Handles both namespaced and non-namespaced pom.xml formats.
    Extracts groupId, artifactId, version, and scope for each dependency.

    Args:
        file_path: Path to the pom.xml file.
        check_crypto: Whether to evaluate cryptographic relevance.

    Returns:
        ParseResult with discovered dependencies and any errors encountered.
    """
    result = ParseResult(
        manifest_path=file_path,
        manifest_type="pom.xml",
    )

    # Handle missing file
    if not os.path.exists(file_path):
        result.success = False
        result.errors.append(f"File not found: {file_path}")
        return result

    # Read file content
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

    # Parse XML
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        result.success = False
        result.errors.append(f"Malformed XML: {e}")
        return result

    # Detect namespace - pom.xml may or may not use the Maven namespace
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    # Extract project-level coordinates
    result.project_group_id = _find_text(root, f"{ns}groupId")
    result.project_artifact_id = _find_text(root, f"{ns}artifactId")
    result.project_version = _find_text(root, f"{ns}version")

    # Extract dependencies from <dependencies> section
    deps_section = root.find(f"{ns}dependencies")
    if deps_section is not None:
        _extract_dependencies(deps_section, ns, result, file_path, check_crypto)

    # Also handle dependencyManagement -> dependencies (may define versions)
    dep_mgmt = root.find(f"{ns}dependencyManagement")
    if dep_mgmt is not None:
        mgmt_deps = dep_mgmt.find(f"{ns}dependencies")
        if mgmt_deps is not None:
            _extract_dependencies(
                mgmt_deps, ns, result, file_path, check_crypto,
                section_prefix="managed-"
            )

    return result


def _find_text(element: ET.Element, tag: str) -> Optional[str]:
    """Find a child element and return its text content."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _extract_dependencies(
    deps_element: ET.Element,
    ns: str,
    result: ParseResult,
    file_path: str,
    check_crypto: bool,
    section_prefix: str = "",
) -> None:
    """Extract dependency elements from a <dependencies> section."""
    for dep in deps_element.findall(f"{ns}dependency"):
        group_id = _find_text(dep, f"{ns}groupId")
        artifact_id = _find_text(dep, f"{ns}artifactId")
        version = _find_text(dep, f"{ns}version")
        scope = _find_text(dep, f"{ns}scope")
        classifier = _find_text(dep, f"{ns}classifier")

        # Use artifactId as the dependency name (primary identifier)
        name = artifact_id or group_id or "unknown"
        version_str = version or "*"

        # Determine the section from scope
        scope_name = scope or "compile"
        section = f"{section_prefix}{scope_name}"

        # Build raw entry for traceability
        raw_parts = []
        if group_id:
            raw_parts.append(f"groupId={group_id}")
        if artifact_id:
            raw_parts.append(f"artifactId={artifact_id}")
        if version:
            raw_parts.append(f"version={version}")
        if scope:
            raw_parts.append(f"scope={scope}")
        raw_entry = ", ".join(raw_parts)

        finding = DependencyFinding(
            name=name,
            version=version_str,
            manifest_path=file_path,
            manifest_type="pom.xml",
            section=section,
            group_id=group_id,
            artifact_id=artifact_id,
            scope=scope,
            raw_entry=raw_entry,
        )

        # Evaluate cryptographic relevance using both artifactId and groupId
        if check_crypto:
            # Check both the artifact ID and group ID for crypto relevance
            artifact_relevance = check_crypto_relevance(artifact_id or "")
            group_relevance = check_crypto_relevance(group_id or "")

            # Merge relevance: if either is relevant, the dependency is relevant
            if artifact_relevance.is_relevant or group_relevance.is_relevant:
                # Use the higher confidence of the two
                reasons = artifact_relevance.reasons + group_relevance.reasons
                best_conf = (
                    artifact_relevance
                    if _confidence_rank(artifact_relevance.confidence)
                    >= _confidence_rank(group_relevance.confidence)
                    else group_relevance
                )
                category = best_conf.crypto_category or artifact_relevance.crypto_category or group_relevance.crypto_category
                finding.crypto_relevance = CryptoRelevance(
                    is_relevant=True,
                    confidence=best_conf.confidence,
                    reasons=reasons,
                    crypto_category=category,
                )
            else:
                finding.crypto_relevance = artifact_relevance

        result.dependencies.append(finding)


def _confidence_rank(confidence: str) -> int:
    """Map confidence string to numeric rank for comparison."""
    return {"high": 3, "medium": 2, "low": 1}.get(confidence, 0)
