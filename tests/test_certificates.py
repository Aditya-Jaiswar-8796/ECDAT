"""Tests for the certificate analyzer (P2 - secondary priority)."""

from modules.certificate_analyzer import analyzer
from tests.fixtures import (
    VALID_CERT,
    INVALID_CERT_TEXT,
    INVALID_CERT_PRIVATE_KEY,
    MISSING_CERT,
)


def test_valid_certificate_parses():
    result = analyzer.analyze_certificate_file(VALID_CERT)
    assert not result.parse_errors
    assert "example.com" in result.subject


def test_subject_and_issuer_extracted():
    result = analyzer.analyze_certificate_file(VALID_CERT)
    assert "commonName=example.com" in result.subject
    assert "Cloudflare" in result.issuer


def test_serial_number_extracted():
    result = analyzer.analyze_certificate_file(VALID_CERT)
    assert result.serial_number
    assert result.serial_number != "unknown"


def test_validity_and_signature_algorithm():
    result = analyzer.analyze_certificate_file(VALID_CERT)
    assert result.not_before is not None
    assert result.not_after is not None
    assert result.signature_algorithm is not None


def test_public_key_metadata():
    result = analyzer.analyze_certificate_file(VALID_CERT)
    assert result.key_type is not None
    assert result.key_size is not None
    assert isinstance(result.key_size, int)


def test_expiry_calculation():
    result = analyzer.analyze_certificate_file(VALID_CERT)
    # example.com certificate is currently valid (fetched live)
    assert result.is_expired is False


def test_private_key_file_rejected():
    result = analyzer.analyze_certificate_file(INVALID_CERT_PRIVATE_KEY)
    assert result.parse_errors
    assert any("private key" in err.lower() for err in result.parse_errors)
    # No private key material must ever leak into the result
    assert result.subject == ""
    assert result.issuer == ""


def test_non_certificate_file_safe():
    result = analyzer.analyze_certificate_file(INVALID_CERT_TEXT)
    assert result.parse_errors
    assert result.subject == ""
    assert result.serial_number == ""


def test_missing_certificate_file_safe():
    result = analyzer.analyze_certificate_file(MISSING_CERT)
    assert result.parse_errors
    assert any("not found" in err for err in result.parse_errors)


def test_directory_scan_bounds():
    # Scan the valid certs directory - must find at least the example cert
    results = analyzer.analyze_certificate_directory("tests/fixtures/valid/certs")
    assert len(results) >= 1


def test_no_private_key_in_any_output():
    """Safety invariant: outputs must never contain private key material."""
    results = analyzer.analyze_certificate_directory("tests/fixtures")
    for finding in results:
        assert "PRIVATE KEY" not in repr(finding)
        assert "BEGIN RSA" not in repr(finding)

    single = analyzer.analyze_certificate_file(VALID_CERT)
    assert "PRIVATE KEY" not in repr(single)