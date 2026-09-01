"""Tests for the unified dependency scanner orchestrator."""

from modules.dependency_scanner import scanner
from tests.fixtures import VALID_DIR, MISSING_PACKAGE_JSON


def test_scanner_discovers_all_manifest_types():
    result = scanner.scan_dependencies(VALID_DIR)
    assert result.total_dependencies >= 20
    assert len(result.manifest_results) == 3

    manifest_types = {r.manifest_type for r in result.manifest_results}
    assert manifest_types == {"package.json", "requirements.txt", "pom.xml"}


def test_scanner_counts_crypto_relevant():
    result = scanner.scan_dependencies(VALID_DIR)
    assert result.crypto_relevant_count > 0
    assert result.crypto_relevant_count <= result.total_dependencies


def test_scanner_single_file_target():
    result = scanner.scan_dependencies(
        r"tests\fixtures\valid\package.json"
    )
    assert result.total_dependencies >= 8
    assert result.manifest_results[0].manifest_type == "package.json"


def test_scanner_can_filter_manifest_types():
    result = scanner.scan_dependencies(
        VALID_DIR, manifest_types=["requirements.txt"]
    )
    assert len(result.manifest_results) == 1
    assert result.manifest_results[0].manifest_type == "requirements.txt"


def test_scanner_nonexistent_path_reports_error():
    result = scanner.scan_dependencies("tests/fixtures/does-not-exist")
    assert len(result.errors) > 0


def test_scanner_skips_no_crash_on_invalid_files():
    # Scan the invalid fixtures dir - must not crash
    result = scanner.scan_dependencies("tests/fixtures/invalid")
    assert result.errors  # some errors reported
    # Exists as a ScanResult regardless
    assert result.manifest_results


def test_scanner_unified_findings_traceable():
    result = scanner.scan_dependencies(VALID_DIR)
    crypto = [d for d in result.all_dependencies if d.crypto_relevance.is_relevant]
    assert len(crypto) > 0
    for dep in crypto:
        assert dep.manifest_path
        assert dep.manifest_type in ("package.json", "requirements.txt", "pom.xml")
        assert dep.raw_entry is not None
        assert dep.crypto_relevance.reasons