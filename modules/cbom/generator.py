"""CBOM (Cryptographic Bill of Materials) generator.

Transforms dependency findings and certificate analysis results into
a structured CBOM-style JSON document. Each entry is traceable back
to its source finding.

This is a hackathon prototype - not a full enterprise CBOM implementation.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CBOMEntry:
    """A single entry in the CBOM, representing a cryptographic asset."""
    id: str
    type: str  # "dependency" or "certificate"
    name: str
    version: str
    source_manifest: str
    manifest_type: str
    section: Optional[str] = None
    crypto_relevance: Optional[str] = None  # "high", "medium", "low"
    crypto_category: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CBOMDocument:
    """Complete CBOM document containing all entries and metadata."""
    format_version: str = "1.0.0"
    tool_version: str = "0.1.0-hackathon"
    generated_at: Optional[str] = None
    project_path: Optional[str] = None
    total_dependencies: int = 0
    crypto_relevant_count: int = 0
    certificate_count: int = 0
    entries: List[CBOMEntry] = field(default_factory=list)
    scan_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def generate_cbom(
    scan_result: Any,
    certificate_findings: Optional[List[Dict[str, Any]]] = None,
    project_path: Optional[str] = None,
) -> CBOMDocument:
    """Generate a CBOM document from scan results and certificate findings.

    Args:
        scan_result: ScanResult from the dependency scanner.
        certificate_findings: Optional list of certificate analysis results.
        project_path: Optional path to the scanned project root.

    Returns:
        CBOMDocument with all entries, traceable to their source findings.
    """
    doc = CBOMDocument(
        generated_at=datetime.now(timezone.utc).isoformat(),
        project_path=project_path or getattr(scan_result, "target_path", "unknown"),
    )

    # Add dependency entries
    if hasattr(scan_result, "all_dependencies"):
        for dep in scan_result.all_dependencies:
            entry = _dependency_to_cbom_entry(dep)
            doc.entries.append(entry)
            doc.total_dependencies += 1
            if dep.crypto_relevance and dep.crypto_relevance.is_relevant:
                doc.crypto_relevant_count += 1

    # Collect scan errors
    if hasattr(scan_result, "errors"):
        doc.scan_errors.extend(scan_result.errors)

    # Add certificate entries
    if certificate_findings:
        for cert_finding in certificate_findings:
            entry = _certificate_to_cbom_entry(cert_finding)
            doc.entries.append(entry)
            doc.certificate_count += 1

    return doc


def _dependency_to_cbom_entry(dep: Any) -> CBOMEntry:
    """Convert a DependencyFinding to a CBOMEntry.

    Preserves full traceability back to the source manifest and finding.
    """
    # Generate a deterministic ID based on manifest + name + version
    id_source = f"{dep.manifest_path}:{dep.name}:{dep.version}"
    entry_id = _generate_id(id_source)

    # Build evidence dictionary for traceability
    evidence = {
        "manifest_path": dep.manifest_path,
        "manifest_type": dep.manifest_type,
        "section": dep.section,
        "raw_entry": dep.raw_entry,
    }

    # Add crypto relevance details
    crypto_relevance = None
    crypto_category = None
    if dep.crypto_relevance and dep.crypto_relevance.is_relevant:
        crypto_relevance = dep.crypto_relevance.confidence
        crypto_category = dep.crypto_relevance.crypto_category
        evidence["crypto_reasons"] = dep.crypto_relevance.reasons

    # Build metadata
    metadata = {}
    if hasattr(dep, "group_id") and dep.group_id:
        metadata["group_id"] = dep.group_id
    if hasattr(dep, "artifact_id") and dep.artifact_id:
        metadata["artifact_id"] = dep.artifact_id
    if hasattr(dep, "scope") and dep.scope:
        metadata["scope"] = dep.scope
    if hasattr(dep, "extras") and dep.extras:
        metadata["extras"] = dep.extras
    if hasattr(dep, "environment_marker") and dep.environment_marker:
        metadata["environment_marker"] = dep.environment_marker
    if dep.parse_errors:
        metadata["parse_errors"] = dep.parse_errors

    return CBOMEntry(
        id=entry_id,
        type="dependency",
        name=dep.name,
        version=dep.version,
        source_manifest=dep.manifest_path,
        manifest_type=dep.manifest_type,
        section=dep.section,
        crypto_relevance=crypto_relevance,
        crypto_category=crypto_category,
        evidence=evidence,
        metadata=metadata,
    )


def _certificate_to_cbom_entry(cert_finding: Dict[str, Any]) -> CBOMEntry:
    """Convert a certificate finding dict to a CBOMEntry.

    Certificate findings come from the certificate analyzer module.
    Only public metadata is included - never private key material.
    """
    subject = cert_finding.get("subject", "unknown")
    issuer = cert_finding.get("issuer", "unknown")
    serial = cert_finding.get("serial_number", "unknown")

    id_source = f"cert:{issuer}:{serial}"
    entry_id = _generate_id(id_source)

    # Build evidence - only public metadata
    evidence = {
        "source_file": cert_finding.get("source_file", "unknown"),
        "subject": subject,
        "issuer": issuer,
        "serial_number": serial,
        "not_before": cert_finding.get("not_before"),
        "not_after": cert_finding.get("not_after"),
        "signature_algorithm": cert_finding.get("signature_algorithm"),
        "key_type": cert_finding.get("key_type"),
        "key_size": cert_finding.get("key_size"),
    }

    # Do NOT include: private_key, private_key_pem, private_key_path, etc.

    metadata = {
        "version": cert_finding.get("version", "unknown"),
        "is_expired": cert_finding.get("is_expired", False),
        "is_self_signed": cert_finding.get("is_self_signed", False),
        "san_dns_names": cert_finding.get("san_dns_names", []),
    }

    return CBOMEntry(
        id=entry_id,
        type="certificate",
        name=f"certificate:{subject}",
        version="1.0",
        source_manifest=cert_finding.get("source_file", "unknown"),
        manifest_type="x509_certificate",
        section=None,
        crypto_relevance="high",  # certificates are always crypto-relevant
        crypto_category="tls",
        evidence=evidence,
        metadata=metadata,
    )


def _generate_id(source: str) -> str:
    """Generate a short deterministic ID from a source string."""
    hash_bytes = hashlib.sha256(source.encode("utf-8")).digest()
    # Take first 12 hex chars for a readable but unique ID
    return hash_bytes[:6].hex()
