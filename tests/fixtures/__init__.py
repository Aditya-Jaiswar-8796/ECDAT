"""Shared helper fixture paths for ECDAT Member 4 tests."""

import os

# Repository root (two levels up from this file)
FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

VALID_DIR = os.path.join(FIXTURES_DIR, "valid")
INVALID_DIR = os.path.join(FIXTURES_DIR, "invalid")

# Valid manifest fixtures
VALID_PACKAGE_JSON = os.path.join(VALID_DIR, "package.json")
VALID_REQUIREMENTS_TXT = os.path.join(VALID_DIR, "requirements.txt")
VALID_POM_XML = os.path.join(VALID_DIR, "pom.xml")
VALID_CERT = os.path.join(VALID_DIR, "certs", "example-com.crt")

# Invalid manifest fixtures
INVALID_PACKAGE_JSON = os.path.join(INVALID_DIR, "package.json")
INVALID_REQUIREMENTS_TXT = os.path.join(INVALID_DIR, "requirements.txt")
INVALID_POM_XML = os.path.join(INVALID_DIR, "pom.xml")
INVALID_CERT_TEXT = os.path.join(INVALID_DIR, "certs", "not-a-cert.txt")
INVALID_CERT_PRIVATE_KEY = os.path.join(INVALID_DIR, "certs", "private-key.pem")

# A path that does not exist on disk
MISSING_PACKAGE_JSON = os.path.join(FIXTURES_DIR, "nonexistent", "package.json")
MISSING_REQUIREMENTS_TXT = os.path.join(FIXTURES_DIR, "nonexistent", "requirements.txt")
MISSING_POM_XML = os.path.join(FIXTURES_DIR, "nonexistent", "pom.xml")
MISSING_CERT = os.path.join(FIXTURES_DIR, "nonexistent", "missing.crt")