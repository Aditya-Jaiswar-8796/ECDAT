"""Tests for CBOM generation and serialization."""

import json

from modules.dependency_scanner import scanner
from modules.certificate_analyzer import analyzer as cert_analyzer
from modules.cbom.generator import generate_cbom
from modules.cbom.serializer import serialize_to_json, serialize_to_dict, save_cbom_json
from tests.fixtures import VALID_DIR, VALID_CERT


def _build_sample_cbom():
    """Create a CBOM from the valid fixtures directory."""
    scan = scanner.scan_dependencies(VALID_DIR)
    cert_findings = cert_analyzer.analyze_certificate_file(VALID_CERT)
    return generate_cbom(
        scan,
        certificate_findings=[
            {
                "source_file": cert_findings.source_file,
                "subject": cert_findings.subject,
                "issuer": cert_findings.issuer,
                "serial_number": cert_findings.serial_number,
                "not_before": cert_findings.not_before,
                "not_after": cert_findings.not_after,
                "signature_algorithm": cert_findings.signature_algorithm,
                "key_type": cert_findings.key_type,
                "key_size": cert_findings.key_size,
                "version": cert_findings.version,
                "is_expired": cert_findings.is_expired,
                "is_self_signed": cert_findings.is_self_signed,
                "san_dns_names": cert_findings.san_dns_names,
            }
        ],
        project_path=VALID_DIR,
    )


def test_cbom_generation_from_real_findings():
    cbom = _build_sample_cbom()
    assert cbom.total_dependencies >= 20
    assert cbom.crypto_relevant_count > 0
    assert cbom.certificate_count == 1
    assert len(cbom.entries) == cbom.total_dependencies + cbom.certificate_count


def test_cbom_entries_traceable_to_findings():
    cbom = _build_sample_cbom()
    dep_entries = [e for e in cbom.entries if e.type == "dependency"]
    crypto_entries = [e for e in dep_entries if e.crypto_relevance]

    # Every crypto entry must carry evidence linking back to source
    for entry in crypto_entries:
        assert entry.evidence["manifest_path"]
        assert entry.evidence["manifest_type"]
        assert entry.evidence["section"] is not None
        assert entry.evidence["raw_entry"] is not None
        assert "crypto_reasons" in entry.evidence

    # A non-crypto entry must not have crypto_reasons
    non_crypto = [e for e in dep_entries if not e.crypto_relevance][0]
    assert "crypto_reasons" not in non_crypto.evidence


def test_cbom_crypto_entries_match_scanner_findings():
    scan = scanner.scan_dependencies(VALID_DIR)
    cbom = generate_cbom(scan, project_path=VALID_DIR)

    scanner_crypto = [
        d for d in scan.all_dependencies if d.crypto_relevance.is_relevant
    ]
    cbom_crypto = [
        e for e in cbom.entries
        if e.type == "dependency" and e.crypto_relevance
    ]
    assert len(cbom_crypto) == len(scanner_crypto)

    # Spot-check that every scanner crypto finding is represented
    scanner_names = {d.name for d in scanner_crypto}
    cbom_names = {e.name for e in cbom_crypto}
    assert scanner_names == cbom_names


def test_cbom_ids_deterministic():
    scan = scanner.scan_dependencies(VALID_DIR)
    cbom1 = generate_cbom(scan, project_path=VALID_DIR)
    cbom2 = generate_cbom(scan, project_path=VALID_DIR)

    ids1 = [e.id for e in cbom1.entries]
    ids2 = [e.id for e in cbom2.entries]
    assert ids1 == ids2


def test_cbom_serialize_to_json_roundtrip():
    cbom = _build_sample_cbom()
    json_str = serialize_to_json(cbom)
    data = json.loads(json_str)

    assert data["format_version"].startswith("1.")
    assert data["summary"]["total_dependencies"] == cbom.total_dependencies
    assert data["summary"]["crypto_relevant_count"] == cbom.crypto_relevant_count
    assert data["summary"]["certificate_count"] == 1

    # Every entry must have traceability fields
    for entry in data["entries"]:
        for field in ("id", "type", "name", "version",
                      "source_manifest", "manifest_type", "evidence"):
            assert field in entry

    # scan_errors is present
    assert isinstance(data["scan_errors"], list)


def test_cbom_serialize_to_dict_structure():
    cbom = _build_sample_cbom()
    data = serialize_to_dict(cbom)
    assert isinstance(data, dict)
    assert "summary" in data
    assert "entries" in data
    assert all(isinstance(e, dict) for e in data["entries"])


def test_cbom_certificate_entry_no_private_key_material():
    cbom = _build_sample_cbom()
    cert_entries = [e for e in cbom.entries if e.type == "certificate"]
    assert len(cert_entries) == 1

    json_str = serialize_to_json(cbom)
    assert "PRIVATE KEY" not in json_str
    assert json_str.count("private") == 0

    cert_entry = cert_entries[0]
    assert cert_entry.crypto_relevance == "high"
    assert cert_entry.evidence["source_file"] is not None


def test_save_cbom_json(tmp_path):
    cbom = _build_sample_cbom()
    out_path = save_cbom_json(cbom, str(tmp_path / "cbom.json"))
    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["summary"]["total_entries"] == len(cbom.entries)


def test_empty_scan_produces_valid_cbom():
    from modules.dependency_scanner.scanner import ScanResult

    scan = ScanResult(target_path="empty")
    cbom = generate_cbom(scan, project_path="empty")
    data = serialize_to_dict(cbom)
    assert data["summary"]["total_entries"] == 0
    # Must still serialize without error
    assert json.loads(serialize_to_json(cbom))["summary"]["total_entries"] == 0