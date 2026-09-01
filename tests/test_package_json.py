"""Tests for the package.json manifest parser."""

from modules.dependency_scanner import package_json
from tests.fixtures import (
    VALID_PACKAGE_JSON,
    INVALID_PACKAGE_JSON,
    MISSING_PACKAGE_JSON,
)


def test_valid_package_json_parses_all_sections():
    result = package_json.parse_package_json(VALID_PACKAGE_JSON)
    assert result.success is True
    assert not result.errors

    names = {d.name for d in result.dependencies}
    # From dependencies
    assert "express" in names
    assert "crypto-js" in names
    assert "lodash" in names
    # From devDependencies
    assert "jest" in names
    # From peerDependencies
    assert "jose" in names


def test_valid_package_json_tracks_manifest_and_section():
    result = package_json.parse_package_json(VALID_PACKAGE_JSON)
    assert result.manifest_type == "package.json"
    assert result.manifest_path == VALID_PACKAGE_JSON

    express = next(d for d in result.dependencies if d.name == "express")
    assert express.section == "dependencies"

    jest = next(d for d in result.dependencies if d.name == "jest")
    assert jest.section == "devDependencies"

    jose = next(d for d in result.dependencies if d.name == "jose")
    assert jose.section == "peerDependencies"


def test_version_extraction():
    result = package_json.parse_package_json(VALID_PACKAGE_JSON)
    versions = {d.name: d.version for d in result.dependencies}
    assert versions["express"] == "^4.18.2"
    assert versions["lodash"] == "4.17.21"
    assert versions["jose"] == "4.14.4"


def test_crypto_relevant_dependencies_detected():
    result = package_json.parse_package_json(VALID_PACKAGE_JSON)
    crypto_names = {
        d.name
        for d in result.dependencies
        if d.crypto_relevance and d.crypto_relevance.is_relevant
    }
    assert "crypto-js" in crypto_names
    assert "jsonwebtoken" in crypto_names
    assert "bcryptjs" in crypto_names
    assert "node-forge" in crypto_names
    assert "jose" in crypto_names


def test_crypto_relevance_has_evidence():
    result = package_json.parse_package_json(VALID_PACKAGE_JSON)
    crypto_js = next(d for d in result.dependencies if d.name == "crypto-js")
    assert crypto_js.crypto_relevance is not None
    assert crypto_js.crypto_relevance.is_relevant is True
    assert crypto_js.crypto_relevance.confidence == "high"
    assert len(crypto_js.crypto_relevance.reasons) > 0
    assert crypto_js.crypto_relevance.crypto_category is not None


def test_non_crypto_dependencies_not_flagged():
    result = package_json.parse_package_json(VALID_PACKAGE_JSON)
    express = next(d for d in result.dependencies if d.name == "express")
    assert express.crypto_relevance.is_relevant is False
    lodash = next(d for d in result.dependencies if d.name == "lodash")
    assert lodash.crypto_relevance.is_relevant is False


def test_raw_entry_evidence_preserved():
    result = package_json.parse_package_json(VALID_PACKAGE_JSON)
    crypto_js = next(d for d in result.dependencies if d.name == "crypto-js")
    assert crypto_js.raw_entry is not None
    assert "crypto-js" in crypto_js.raw_entry
    assert "^4.1.1" in crypto_js.raw_entry


def test_malformed_package_json_reports_error_without_crash():
    result = package_json.parse_package_json(INVALID_PACKAGE_JSON)
    assert result.success is False
    assert len(result.errors) > 0
    assert any("Invalid JSON" in err for err in result.errors)
    # Pipeline must not crash - return a parse result object
    assert result.dependencies == []


def test_missing_package_json_reports_error():
    result = package_json.parse_package_json(MISSING_PACKAGE_JSON)
    assert result.success is False
    assert any("not found" in err for err in result.errors)


def test_empty_file_content():
    import json
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        tmp.write("")
        tmp_path = tmp.name
    try:
        result = package_json.parse_package_json(tmp_path)
        assert result.success is False
        assert any("empty" in err for err in result.errors)
    finally:
        os.unlink(tmp_path)


def test_non_object_root_reports_error():
    import json
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        tmp.write(json.dumps([1, 2, 3]))
        tmp_path = tmp.name
    try:
        result = package_json.parse_package_json(tmp_path)
        assert result.success is False
        assert any("not a JSON object" in err for err in result.errors)
    finally:
        os.unlink(tmp_path)


def test_unpinned_version_handled_safely():
    import tempfile
    import os

    content = '{"name": "t", "dependencies": {"crypto-js": "*"}}'
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = package_json.parse_package_json(tmp_path)
        assert result.success is True
        crypto_js = next(d for d in result.dependencies if d.name == "crypto-js")
        assert crypto_js.version in ("*", "")
    finally:
        os.unlink(tmp_path)