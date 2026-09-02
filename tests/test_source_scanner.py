import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from modules.source_scanner import file_discovery
from modules.source_scanner.evidence import read_source_lines
from modules.source_scanner.scanner import scan, scan_directory, scan_file

FIXTURES = REPO_ROOT / "tests" / "fixtures"
JAVA_DIR = FIXTURES / "java"
PYTHON_DIR = FIXTURES / "python"
JS_DIR = FIXTURES / "js"

EXPECTED_KEYS = {
    "id", "algorithm", "operation", "key_size", "language", "library", "api",
    "file_path", "line_number", "evidence", "confidence",
    "business_criticality", "data_lifetime_years", "internet_exposure",
    "migration_complexity", "risk_score", "risk_level", "migration_priority",
    "mosca_assessment", "recommendation",
}


class FileDiscoveryTests(unittest.TestCase):

    def test_recursive_discovery_finds_nested_files(self):
        found = file_discovery.discover_source_files(str(JAVA_DIR))
        self.assertEqual(len(found), 3)
        self.assertTrue(any(f.endswith("crypto_app.java") for f in found))
        self.assertTrue(any(f.endswith("plain.java") for f in found))
        self.assertTrue(any(f.endswith("malformed.java") for f in found))

    def test_discovery_skips_unsupported_extensions(self):
        found = file_discovery.discover_source_files(str(PYTHON_DIR))
        for path in found:
            self.assertTrue(path.endswith(".py"))

    def test_ignored_directory_filtering(self):
        found = file_discovery.discover_source_files(str(FIXTURES / "scanner_test_tree"))
        self.assertTrue(any(f.endswith("app.py") for f in found))
        self.assertFalse(any("node_modules" in f for f in found))

    def test_ignored_directory_matches_known_set(self):
        required = {".git", "node_modules", "build", "dist", "__pycache__", ".next", "target"}
        self.assertTrue(required.issubset(file_discovery.IGNORED_DIRS))

    def test_discovery_raises_on_missing_root(self):
        with self.assertRaises(FileNotFoundError):
            file_discovery.discover_source_files(str(FIXTURES / "does_not_exist"))

    def test_language_detection(self):
        self.assertEqual(file_discovery.detect_language("a.java"), "java")
        self.assertEqual(file_discovery.detect_language("a.py"), "python")
        self.assertEqual(file_discovery.detect_language("a.js"), "javascript")
        self.assertEqual(file_discovery.detect_language("a.mjs"), "javascript")
        self.assertEqual(file_discovery.detect_language("a.ts"), "typescript")
        self.assertEqual(file_discovery.detect_language("a.tsx"), "typescript")
        self.assertIsNone(file_discovery.detect_language("a.txt"))


class FindingShapeTests(unittest.TestCase):

    def test_findings_have_exact_cryptoasset_keys(self):
        result = scan_directory(str(JAVA_DIR))
        self.assertGreater(result["total_findings"], 0)
        for finding in result["findings"]:
            self.assertEqual(set(finding.keys()), EXPECTED_KEYS, finding)

    def test_downstream_fields_start_unset(self):
        result = scan_directory(str(JAVA_DIR))
        for finding in result["findings"]:
            self.assertIsNone(finding["risk_score"])
            self.assertIsNone(finding["risk_level"])
            self.assertIsNone(finding["migration_priority"])
            self.assertIsNone(finding["mosca_assessment"])
            self.assertIsNone(finding["recommendation"])
            self.assertIsNone(finding["business_criticality"])
            self.assertIsNone(finding["data_lifetime_years"])
            self.assertIsNone(finding["internet_exposure"])
            self.assertIsNone(finding["migration_complexity"])
            self.assertIsNone(finding["id"])


class JavaDetectionTests(unittest.TestCase):

    def test_java_detects_cipher_and_algorithm(self):
        findings = scan_file(str(JAVA_DIR / "crypto_app.java"))
        cipher_findings = [f for f in findings if f["api"] == "Cipher.getInstance"]
        self.assertEqual(len(cipher_findings), 1)
        f = cipher_findings[0]
        self.assertEqual(f["algorithm"], "RSA")
        self.assertEqual(f["operation"], "encryption")
        self.assertEqual(f["language"], "java")
        self.assertEqual(f["library"], "javax.crypto")
        self.assertEqual(f["line_number"], 12)
        self.assertEqual(f["confidence"], "HIGH")

    def test_java_detects_message_digest(self):
        findings = scan_file(str(JAVA_DIR / "crypto_app.java"))
        digest_findings = [f for f in findings if f["api"] == "MessageDigest.getInstance"]
        self.assertEqual(len(digest_findings), 1)
        f = digest_findings[0]
        self.assertEqual(f["algorithm"], "SHA-256")
        self.assertEqual(f["operation"], "hashing")
        self.assertEqual(f["line_number"], 18)
        self.assertEqual(f["confidence"], "HIGH")

    def test_java_detects_key_generation(self):
        findings = scan_file(str(JAVA_DIR / "crypto_app.java"))
        keygen_findings = [f for f in findings if f["api"] == "KeyPairGenerator.getInstance"]
        self.assertEqual(len(keygen_findings), 1)
        f = keygen_findings[0]
        self.assertEqual(f["algorithm"], "RSA")
        self.assertEqual(f["operation"], "key_generation")
        self.assertEqual(f["line_number"], 24)
        self.assertEqual(f["confidence"], "HIGH")

    def test_java_plain_file_has_no_findings(self):
        findings = scan_file(str(JAVA_DIR / "plain.java"))
        self.assertEqual(findings, [])

    def test_java_evidence_contains_source_line(self):
        findings = scan_file(str(JAVA_DIR / "crypto_app.java"))
        f = [x for x in findings if x["api"] == "Cipher.getInstance"][0]
        self.assertIn("Cipher.getInstance", f["evidence"])
        self.assertIn("12:", f["evidence"])


class PythonDetectionTests(unittest.TestCase):

    def test_python_detects_hashlib_sha512(self):
        findings = scan_file(str(PYTHON_DIR / "crypto_app.py"))
        sha_findings = [f for f in findings if f["api"] == "hashlib.sha512"]
        self.assertEqual(len(sha_findings), 1)
        f = sha_findings[0]
        self.assertEqual(f["algorithm"], "SHA-512")
        self.assertEqual(f["operation"], "hashing")
        self.assertEqual(f["library"], "hashlib")
        self.assertEqual(f["line_number"], 9)
        self.assertEqual(f["language"], "python")
        self.assertEqual(f["confidence"], "HIGH")

    def test_python_detects_hashlib_new(self):
        findings = scan_file(str(PYTHON_DIR / "crypto_app.py"))
        new_findings = [f for f in findings if f["api"] == "hashlib.new"]
        self.assertEqual(len(new_findings), 1)
        self.assertEqual(new_findings[0]["algorithm"], "SHA-1")
        self.assertEqual(new_findings[0]["line_number"], 14)

    def test_python_detects_hmac(self):
        findings = scan_file(str(PYTHON_DIR / "crypto_app.py"))
        hmac_findings = [f for f in findings if f["api"] == "hmac.new"]
        self.assertEqual(len(hmac_findings), 1)
        self.assertEqual(hmac_findings[0]["line_number"], 21)
        self.assertEqual(hmac_findings[0]["operation"], "mac")

    def test_python_detects_os_urandom(self):
        findings = scan_file(str(PYTHON_DIR / "crypto_app.py"))
        rand_findings = [f for f in findings if f["api"] == "os.urandom"]
        self.assertEqual(len(rand_findings), 1)
        self.assertEqual(rand_findings[0]["line_number"], 26)
        self.assertEqual(rand_findings[0]["confidence"], "MEDIUM")

    def test_python_plain_file_has_no_findings(self):
        findings = scan_file(str(PYTHON_DIR / "plain.py"))
        self.assertEqual(findings, [])


class JavaScriptDetectionTests(unittest.TestCase):

    def test_js_detects_create_hash(self):
        findings = scan_file(str(JS_DIR / "crypto_app.js"))
        hash_findings = [f for f in findings if f["api"] == "crypto.createHash"]
        self.assertEqual(len(hash_findings), 1)
        f = hash_findings[0]
        self.assertEqual(f["algorithm"], "sha256")
        self.assertEqual(f["operation"], "hashing")
        self.assertEqual(f["library"], "node:crypto")
        self.assertEqual(f["line_number"], 5)
        self.assertEqual(f["language"], "javascript")
        self.assertEqual(f["confidence"], "HIGH")

    def test_js_detects_create_cipheriv(self):
        findings = scan_file(str(JS_DIR / "crypto_app.js"))
        cipher_findings = [f for f in findings if f["api"] == "crypto.createCipheriv"]
        self.assertEqual(len(cipher_findings), 1)
        f = cipher_findings[0]
        self.assertEqual(f["algorithm"], "aes-256-gcm")
        self.assertEqual(f["operation"], "encryption")
        self.assertEqual(f["line_number"], 8)
        self.assertEqual(f["confidence"], "HIGH")

    def test_js_detects_random_bytes(self):
        findings = scan_file(str(JS_DIR / "crypto_app.js"))
        rand_findings = [f for f in findings if f["api"] == "crypto.randomBytes"]
        self.assertEqual(len(rand_findings), 1)
        self.assertEqual(rand_findings[0]["line_number"], 11)
        self.assertEqual(rand_findings[0]["operation"], "randomness")

    def test_ts_file_reports_typescript_language(self):
        findings = scan_file(str(JS_DIR / "crypto_app.ts"))
        subtle_findings = [f for f in findings if f["api"] == "crypto.subtle.digest"]
        self.assertEqual(len(subtle_findings), 1)
        self.assertEqual(subtle_findings[0]["language"], "typescript")
        self.assertEqual(subtle_findings[0]["algorithm"], "SHA-256")
        self.assertEqual(subtle_findings[0]["confidence"], "HIGH")

    def test_ts_import_emits_low_confidence_finding(self):
        findings = scan_file(str(JS_DIR / "crypto_app.ts"))
        import_findings = [f for f in findings if f["api"] == "crypto (import)"]
        self.assertEqual(len(import_findings), 1)
        self.assertEqual(import_findings[0]["confidence"], "LOW")

    def test_js_plain_file_has_no_findings(self):
        findings = scan_file(str(JS_DIR / "plain.js"))
        self.assertEqual(findings, [])


class MalformedSourceTests(unittest.TestCase):

    def test_java_malformed_still_detects_and_recovers(self):
        findings = scan_file(str(JAVA_DIR / "malformed.java"))
        self.assertGreater(len(findings), 0)
        self.assertTrue(any(f["api"] == "Cipher.getInstance" for f in findings))

    def test_python_malformed_still_detects_and_recovers(self):
        findings = scan_file(str(PYTHON_DIR / "malformed.py"))
        self.assertGreater(len(findings), 0)
        self.assertTrue(any(f["api"] == "hashlib.md5" for f in findings))

    def test_directory_scan_never_raises_on_bad_files(self):
        result = scan_directory(str(FIXTURES))
        self.assertIn("findings", result)
        self.assertGreater(result["files_scanned"], 0)

    def test_missing_file_returns_no_findings(self):
        findings = scan_file(str(FIXTURES / "nope.py"))
        self.assertEqual(findings, [])


class ConfidenceTests(unittest.TestCase):

    def _get_confidence(self, path: str, api: str) -> str:
        findings = scan_file(path)
        return [f for f in findings if f["api"] == api][0]["confidence"]

    def test_high_when_algorithm_known(self):
        java = self._get_confidence(str(JAVA_DIR / "crypto_app.java"), "Cipher.getInstance")
        self.assertEqual(java, "HIGH")

    def test_medium_when_algorithm_missing(self):
        python_rand = self._get_confidence(str(PYTHON_DIR / "crypto_app.py"), "os.urandom")
        self.assertEqual(python_rand, "MEDIUM")

    def test_low_for_weak_import_signal(self):
        ts_import = self._get_confidence(str(JS_DIR / "crypto_app.ts"), "crypto (import)")
        self.assertEqual(ts_import, "LOW")


class DemoRepositoryTests(unittest.TestCase):

    def test_demo_repository_scan_finds_all_language_findings(self):
        result = scan_directory(str(REPO_ROOT / "demo_repository"))
        languages = {f["language"] for f in result["findings"]}
        self.assertTrue({"java", "python", "javascript", "typescript"} <= languages)
        self.assertGreater(result["total_findings"], 0)

    def test_demo_repository_ignores_build_and_modules_dirs(self):
        result = scan_directory(str(REPO_ROOT / "demo_repository"))
        all_paths = [f["file_path"] for f in result["findings"]]
        self.assertFalse(any("target" in p for p in all_paths))
        self.assertFalse(any("node_modules" in p for p in all_paths))

    def test_demo_repository_fernet_detected(self):
        result = scan_directory(str(REPO_ROOT / "demo_repository"))
        fernet = [f for f in result["findings"] if "Fernet" in f["api"]]
        self.assertGreaterEqual(len(fernet), 1)
        self.assertTrue(any(f["operation"] == "symmetric_encryption" for f in fernet))
        file_paths = [f["file_path"] for f in fernet]
        self.assertTrue(all("token_encryptor.py" in p for p in file_paths))


class SingleFileScanTests(unittest.TestCase):

    def test_scan_single_file(self):
        result = scan(str(JAVA_DIR / "crypto_app.java"))
        self.assertEqual(result["files_scanned"], 1)
        self.assertEqual(result["total_findings"], len(result["findings"]))
        self.assertGreater(result["total_findings"], 0)

    def test_scan_single_file_no_crypto(self):
        result = scan(str(JAVA_DIR / "plain.java"))
        self.assertEqual(result["total_findings"], 0)


class EvidenceHelperTests(unittest.TestCase):

    def test_read_source_lines_returns_list(self):
        lines = read_source_lines(str(PYTHON_DIR / "crypto_app.py"))
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)

    def test_read_source_lines_missing_file_is_empty(self):
        self.assertEqual(read_source_lines(str(FIXTURES / "absent.py")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)