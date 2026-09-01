"""Tests for the Maven pom.xml manifest parser."""

from modules.dependency_scanner import pom_xml
from tests.fixtures import (
    VALID_POM_XML,
    INVALID_POM_XML,
    MISSING_POM_XML,
)


def test_valid_pom_xml_parses():
    result = pom_xml.parse_pom_xml(VALID_POM_XML)
    assert result.success is True
    assert not result.errors

    names = {d.name for d in result.dependencies}
    assert "spring-core" in names
    assert "spring-security-crypto" in names
    assert "bcprov-jdk18on" in names
    assert "bcpkix-jdk18on" in names
    assert "java-jwt" in names
    assert "gson" in names


def test_project_coordinates_extracted():
    result = pom_xml.parse_pom_xml(VALID_POM_XML)
    assert result.project_group_id == "com.ecdat.demo"
    assert result.project_artifact_id == "ecdat-demo-service"
    assert result.project_version == "1.0.0"


def test_group_and_artifact_tracking():
    result = pom_xml.parse_pom_xml(VALID_POM_XML)
    bcprov = next(d for d in result.dependencies if d.name == "bcprov-jdk18on")
    assert bcprov.group_id == "org.bouncycastle"
    assert bcprov.artifact_id == "bcprov-jdk18on"
    assert bcprov.version == "1.74"


def test_scope_and_section_tracking():
    result = pom_xml.parse_pom_xml(VALID_POM_XML)
    spring_core = next(d for d in result.dependencies if d.name == "spring-core")
    assert spring_core.scope is None  # default compile
    assert spring_core.section == "compile"

    bcpkix = next(d for d in result.dependencies if d.name == "bcpkix-jdk18on")
    assert bcpkix.scope == "test"
    assert bcpkix.section == "test"


def test_template_versions_preserved():
    result = pom_xml.parse_pom_xml(VALID_POM_XML)
    spring_core = next(d for d in result.dependencies if d.name == "spring-core")
    assert spring_core.version == "${spring.version}"


def test_crypto_relevant_dependencies_detected():
    result = pom_xml.parse_pom_xml(VALID_POM_XML)
    crypto_names = {
        d.name
        for d in result.dependencies
        if d.crypto_relevance and d.crypto_relevance.is_relevant
    }
    assert "spring-security-crypto" in crypto_names
    assert "bcprov-jdk18on" in crypto_names
    assert "bcpkix-jdk18on" in crypto_names
    assert "java-jwt" in crypto_names

    # Non-crypto dependency must not be flagged
    gson = next(d for d in result.dependencies if d.name == "gson")
    assert gson.crypto_relevance.is_relevant is False


def test_crypto_evidence_generation():
    result = pom_xml.parse_pom_xml(VALID_POM_XML)
    bcprov = next(d for d in result.dependencies if d.name == "bcprov-jdk18on")
    assert bcprov.crypto_relevance.is_relevant is True
    assert len(bcprov.crypto_relevance.reasons) > 0
    assert bcprov.raw_entry is not None
    assert "org.bouncycastle" in bcprov.raw_entry


def test_malformed_pom_xml_returns_error_not_crash():
    result = pom_xml.parse_pom_xml(INVALID_POM_XML)
    assert result.success is False
    assert len(result.errors) > 0
    assert any("Malformed XML" in err for err in result.errors)
    assert result.dependencies == []


def test_missing_pom_xml_reports_error():
    result = pom_xml.parse_pom_xml(MISSING_POM_XML)
    assert result.success is False
    assert any("not found" in err for err in result.errors)


def test_empty_pom_xml_reports_error():
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False
    ) as tmp:
        tmp.write("")
        tmp_path = tmp.name
    try:
        result = pom_xml.parse_pom_xml(tmp_path)
        assert result.success is False
        assert any("empty" in err for err in result.errors)
    finally:
        os.unlink(tmp_path)


def test_namespace_and_non_namespace_xml():
    import tempfile
    import os

    # pom.xml without the Maven namespace declaration
    content = """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>no-ns-app</artifactId>
  <dependencies>
    <dependency>
      <groupId>org.python</groupId>
      <artifactId>bcrypt</artifactId>
      <version>0.4</version>
    </dependency>
  </dependencies>
</project>
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = pom_xml.parse_pom_xml(tmp_path)
        assert result.success is True
        assert len(result.dependencies) == 1
        assert result.dependencies[0].artifact_id == "bcrypt"
        assert result.dependencies[0].crypto_relevance.is_relevant is True
    finally:
        os.unlink(tmp_path)