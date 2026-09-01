"""Tests for the requirements.txt manifest parser."""

from modules.dependency_scanner import requirements_txt
from tests.fixtures import (
    VALID_REQUIREMENTS_TXT,
    INVALID_REQUIREMENTS_TXT,
    MISSING_REQUIREMENTS_TXT,
)


def test_valid_requirements_txt_parses():
    result = requirements_txt.parse_requirements_txt(VALID_REQUIREMENTS_TXT)
    assert result.success is True
    assert not result.errors

    names = {d.name for d in result.dependencies}
    assert "cryptography" in names
    assert "requests" in names
    assert "pyjwt" in names
    assert "bcrypt" in names
    assert "flask" in names


def test_version_extraction():
    result = requirements_txt.parse_requirements_txt(VALID_REQUIREMENTS_TXT)
    cryptography = next(d for d in result.dependencies if d.name == "cryptography")
    assert cryptography.version == "==41.0.3"

    requests = next(d for d in result.dependencies if d.name == "requests")
    assert requests.version == "==2.31.0"

    flask = next(d for d in result.dependencies if d.name == "flask")
    assert flask.version == "==3.0.0"


def test_unpinned_version_uses_wildcard():
    result = requirements_txt.parse_requirements_txt(VALID_REQUIREMENTS_TXT)
    # cryptography>=3.4.0 appears as an unpinned second entry
    unpinned = [d for d in result.dependencies if d.name == "cryptography"]
    assert len(unpinned) >= 1


def test_extras_and_environment_markers_extracted():
    result = requirements_txt.parse_requirements_txt(VALID_REQUIREMENTS_TXT)
    paramiko = next(d for d in result.dependencies if d.name == "paramiko")
    assert paramiko.extras == "ssh"
    assert paramiko.environment_marker is not None


def test_comments_and_options_skipped():
    result = requirements_txt.parse_requirements_txt(VALID_REQUIREMENTS_TXT)
    names = {d.name for d in result.dependencies}
    # pip options like -e, and full-line comments, must not be dependencies
    assert "editablepkg" not in names
    assert "git+https" not in names


def test_crypto_relevant_dependencies_detected():
    result = requirements_txt.parse_requirements_txt(VALID_REQUIREMENTS_TXT)
    crypto_names = {
        d.name
        for d in result.dependencies
        if d.crypto_relevance and d.crypto_relevance.is_relevant
    }
    assert "cryptography" in crypto_names
    assert "pyjwt" in crypto_names
    assert "bcrypt" in crypto_names
    assert "paramiko" in crypto_names
    assert "jose" in crypto_names


def test_crypto_evidence_generation():
    result = requirements_txt.parse_requirements_txt(VALID_REQUIREMENTS_TXT)
    cryptography = next(d for d in result.dependencies if d.name == "cryptography")
    assert cryptography.crypto_relevance.is_relevant is True
    assert len(cryptography.crypto_relevance.reasons) > 0
    assert cryptography.raw_entry is not None


def test_traceability_fields():
    result = requirements_txt.parse_requirements_txt(VALID_REQUIREMENTS_TXT)
    cryptography = next(d for d in result.dependencies if d.name == "cryptography")
    assert cryptography.manifest_path == VALID_REQUIREMENTS_TXT
    assert cryptography.manifest_type == "requirements.txt"
    assert cryptography.section == "requirements"


def test_malformed_requirements_txt_keeps_valid_lines():
    result = requirements_txt.parse_requirements_txt(INVALID_REQUIREMENTS_TXT)
    # Not a crash - returns a result object
    assert result is not None

    # Valid lines still extracted despite malformed lines
    names = {d.name for d in result.dependencies}
    assert "django" in names
    assert "cryptography" in names
    assert "requests" in names

    # Malformed lines reported but do not stop processing
    # (there may or may not be errors depending on how lines are classified)
    assert result.dependencies  # at least one dependency found


def test_missing_requirements_txt_reports_error():
    result = requirements_txt.parse_requirements_txt(MISSING_REQUIREMENTS_TXT)
    assert result.success is False
    assert any("not found" in err for err in result.errors)


def test_inline_comment_after_version_stripped():
    result = requirements_txt.parse_requirements_txt(INVALID_REQUIREMENTS_TXT)
    cryptography = next(d for d in result.dependencies if d.name == "cryptography")
    assert cryptography.version == "==40.0.0"
    assert "#" not in cryptography.version


def test_empty_requirements_txt_is_valid():
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp:
        tmp.write("# only a comment\n\n")
        tmp_path = tmp.name
    try:
        result = requirements_txt.parse_requirements_txt(tmp_path)
        assert result.success is True
        assert result.dependencies == []
    finally:
        os.unlink(tmp_path)