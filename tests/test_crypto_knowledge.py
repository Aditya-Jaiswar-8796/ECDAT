import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from modules.crypto_knowledge import (
    base_score_for,
    canonical_operation,
    find_fallback,
    load_algorithm_knowledge,
    load_methodology,
    load_recommendations,
    resolve_algorithm,
    risk_level_for,
)

from modules.source_scanner.detectors import java, javascript, python

CORE_ALGORITHM_IDS = {
    "RSA", "ECC", "ECDSA", "ECDH", "AES", "3DES", "DES",
    "MD5", "SHA-1", "SHA-256", "ML-KEM", "ML-DSA",
}

VALID_FAMILIES = {"asymmetric", "symmetric", "hash", "pqc"}
VALID_LEGACY_STATUS = {
    "BROKEN", "DEPRECATED", "TRANSITIONAL", "ACTIVE", "PQC_RECOMMENDED",
}
VALID_QUANTUM_SEVERITY = {"NONE", "LOW", "MEDIUM", "HIGH"}


def _m3_operations() -> set:
    ops = set()
    for library, operation in java.API_OPERATIONS.values():
        ops.add(operation)
    for table in (
        javascript.NODE_CRYPTO_FUNCS,
        javascript.WEB_CRYPTO_SUBTLE_FUNCS,
    ):
        for value in table.values():
            ops.add(value)
    for library, operation in python.STANDALONE_PATTERNS.values():
        ops.add(operation)
    ops.add("crypto_import")  # hard-coded in the JavaScript detector
    return ops


class CryptoKnowledgeDocumentTests(unittest.TestCase):

    def test_all_documents_are_valid_json(self):
        for filename in ("crypto_knowledge.json", "methodology.json",
                         "recommendations.json"):
            path = Path(__file__).parent.parent / "modules" / "crypto_knowledge" / filename
            with path.open("r", encoding="utf-8") as handle:
                json.load(handle)

    def test_core_algorithm_coverage(self):
        knowledge = load_algorithm_knowledge()
        ids = {entry["id"] for entry in knowledge["core_algorithms"]}
        self.assertEqual(ids, CORE_ALGORITHM_IDS)

    def test_core_entries_have_required_fields(self):
        required = {
            "id", "family", "aliases", "uses", "quantum_concern",
            "legacy_status", "base_risk_score", "notes",
        }
        for entry in load_algorithm_knowledge()["core_algorithms"]:
            self.assertTrue(required.issubset(entry.keys()), entry["id"])
            self.assertIn(entry["family"], VALID_FAMILIES)
            self.assertIn(entry["legacy_status"], VALID_LEGACY_STATUS)
            self.assertIn(
                entry["quantum_concern"]["severity"], VALID_QUANTUM_SEVERITY,
            )
            self.assertIsInstance(entry["aliases"], list)
            self.assertIsInstance(entry["uses"], list)

    def test_base_risk_scores_are_bounded(self):
        knowledge = load_algorithm_knowledge()
        entries = knowledge["core_algorithms"]
        entries += [
            {"id": key, **value}
            for key, value in knowledge["extended_algorithms"]["entries"].items()
        ]
        for entry in entries:
            score = float(entry["base_risk_score"])
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 10.0)

    def test_operations_documented(self):
        knowledge = load_algorithm_knowledge()
        documented = set(knowledge["operations"].keys())
        for entry in knowledge["core_algorithms"]:
            for use in entry["uses"]:
                self.assertIn(use, documented)

    def test_no_invented_quantum_dates(self):
        docs = (
            load_algorithm_knowledge(),
            load_methodology(),
            load_recommendations(),
        )

        def walk(value):
            for key in ("arrival", "arrival_date", "quantum_date",
                        "quantum_year", "impact_year"):
                if isinstance(value, dict) and key in value:
                    self.fail(f"forbidden timeline key: {key}")
            if isinstance(value, dict):
                for k, v in value.items():
                    walk(k)
                    walk(v)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
            elif isinstance(value, str):
                # Guard against asserted quantum/crypto timeline dates. Key
                # sizes (2048, 3072, 4096) and FIPS numbers (204) can look
                # like years, so every matched future-year token must be one
                # of the known key-size numbers.
                tokens = re.findall(
                    r"\b(20(?:3\d|4\d|5\d|6\d|7\d|8\d|9\d)|21\d\d)\b",
                    value,
                )
                unexpected = [t for t in tokens if t not in
                              {"2048", "3072", "4096"}]
                if unexpected:
                    self.fail(
                        f"document embeds a future year {unexpected}: {value!r}",
                    )

        for doc in docs:
            walk(doc)

        methodology = load_methodology()
        horizon = methodology["mosca_model"]["configurable_parameters"][
            "planning_horizon_years"
        ]
        self.assertIs(horizon["is_assumption"], True)

    def test_planning_horizon_used_in_principles(self):
        methodology = load_methodology()
        joined = " ".join(methodology["principles"]).lower()
        self.assertIn("planning horizon", joined)
        self.assertIn("mosca", joined)


class MethodologyDocumentTests(unittest.TestCase):

    def test_risk_level_thresholds_cover_0_to_10(self):
        thresholds = load_methodology()["risk_level_thresholds"]
        order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        previous_max = None
        for level in order:
            band = thresholds[level]
            self.assertGreaterEqual(band["min"], 0.0)
            self.assertLessEqual(band["max"], 10.0)
            if previous_max is not None:
                self.assertAlmostEqual(band["min"], previous_max + 0.1)
            previous_max = band["max"]
        self.assertAlmostEqual(thresholds["LOW"]["min"], 0.0)
        self.assertAlmostEqual(thresholds["CRITICAL"]["max"], 10.0)

    def test_factor_deltas_are_finite_and_bounded(self):
        for factor in load_methodology()["risk_factors"]:
            delta = float(factor["score_delta"])
            self.assertGreaterEqual(delta, 0.0)
            self.assertLessEqual(delta, 2.0)

    def test_priority_promotions_cap_at_urgent(self):
        rules = load_methodology()["migration_priority_rules"]
        for promotion in rules["promotions"]:
            self.assertIn("URGENT", promotion["effect"])
        self.assertEqual(rules["base_mapping"]["CRITICAL"], "URGENT")

    def test_key_size_adjustments_present(self):
        adjustments = load_methodology()["risk_score_definition"][
            "key_size_adjustments"
        ]
        self.assertIn("RSA", adjustments)
        self.assertIn("ECC", adjustments)
        self.assertIn("AES", adjustments)
        for table in adjustments.values():
            for size, delta in table.items():
                self.assertTrue(str(int(size)) == size)
                self.assertIsInstance(delta, (int, float))


class M3MappingReviewTests(unittest.TestCase):

    def test_every_m3_operation_has_fallback_and_mapping(self):
        methodology = load_methodology()
        mapping = methodology["m3_operation_mapping"]["mapping"]
        knowledge = load_algorithm_knowledge()
        fallback_ops = {rule["operation"] for rule in
                        knowledge["fallback_rules"]["rules"]}

        for operation in _m3_operations():
            self.assertIn(operation, mapping, f"no mapping for {operation}")
            self.assertIn(operation, fallback_ops, f"no fallback for {operation}")

    def test_canonical_operation_aliases(self):
        self.assertEqual(
            canonical_operation("key_agreement")["canonical"],
            "key_establishment",
        )
        self.assertEqual(canonical_operation("hash")["canonical"], "hashing")


class RecommendationsTests(unittest.TestCase):

    def test_per_algorithm_covers_core_set(self):
        recommendations = load_recommendations()
        recommended = {entry["algorithm"] for entry in
                       recommendations["per_algorithm"]}
        self.assertEqual(recommended, CORE_ALGORITHM_IDS)

    def test_actions_follow_action_vocabulary(self):
        vocabulary = set(load_recommendations()["action_vocabulary"].keys())
        for entry in load_recommendations()["per_algorithm"]:
            self.assertIn(entry["action"], vocabulary)


class ResolutionAndScoringTests(unittest.TestCase):

    def test_alias_resolution(self):
        self.assertEqual(resolve_algorithm("DESede")["id"], "3DES")
        self.assertEqual(resolve_algorithm("aes-256-gcm")["id"], "AES")
        self.assertEqual(resolve_algorithm("P-256")["id"], "ECC")
        self.assertEqual(resolve_algorithm("Kyber")["id"], "ML-KEM")
        self.assertEqual(resolve_algorithm("AES-128-CBC (Fernet)")["id"], "AES")

    def test_base_scores(self):
        self.assertEqual(base_score_for("RSA")["base_risk_score"], 7.0)
        self.assertEqual(base_score_for("SHA-256")["base_risk_score"], 1.0)
        self.assertEqual(base_score_for("ML-KEM")["base_risk_score"], 0.0)
        self.assertEqual(base_score_for("DESede")["base_risk_score"], 9.0)

    def test_key_size_adjustments(self):
        self.assertEqual(
            base_score_for("RSA", "encryption", 1024)["base_risk_score"], 9.0,
        )
        self.assertEqual(
            base_score_for("AES", "symmetric_encryption", 128)["base_risk_score"],
            2.0,
        )
        self.assertEqual(
            base_score_for("ECDSA", "signature", 256)["base_risk_score"], 7.0,
        )

    def test_fallback_scoring_and_review_flag(self):
        result = base_score_for(None, "hashing")
        self.assertEqual(result["resolution"], "fallback")
        self.assertIs(result["review_required"], True)
        self.assertEqual(result["base_risk_score"], 5.0)
        fallback = find_fallback("signature")
        self.assertEqual(fallback["fallback_base_risk_score"], 7.0)

    def test_risk_level_mapping(self):
        self.assertEqual(risk_level_for(3.9), "LOW")
        self.assertEqual(risk_level_for(4.0), "MEDIUM")
        self.assertEqual(risk_level_for(7.0), "HIGH")
        self.assertEqual(risk_level_for(9.0), "CRITICAL")
        self.assertEqual(risk_level_for(10.0), "CRITICAL")


if __name__ == "__main__":
    unittest.main()