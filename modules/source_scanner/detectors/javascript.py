from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base import make_finding
from ..evidence import build_snippet, clean_algorithm_text
from ..file_discovery import detect_language

NODE_CRYPTO_FUNCS: Dict[str, str] = {
    "createHash": "hashing",
    "createCipher": "encryption",
    "createCipheriv": "encryption",
    "createDecipher": "decryption",
    "createDecipheriv": "decryption",
    "createHmac": "mac",
    "createSign": "signature",
    "createVerify": "signature",
    "createECDH": "key_agreement",
    "generateKeyPair": "key_generation",
    "generateKeyPairSync": "key_generation",
    "randomBytes": "randomness",
    "pbkdf2": "key_derivation",
    "scrypt": "key_derivation",
    "publicEncrypt": "encryption",
    "privateDecrypt": "decryption",
    "sign": "signature",
    "verify": "signature",
}

WEB_CRYPTO_SUBTLE_FUNCS: Dict[str, str] = {
    "digest": "hashing",
    "encrypt": "encryption",
    "decrypt": "decryption",
    "generateKey": "key_generation",
    "importKey": "key_import",
    "deriveKey": "key_derivation",
    "deriveBits": "key_derivation",
    "sign": "signature",
    "verify": "signature",
}

KNOWN_ALGORITHMS: List[str] = [
    "sha256", "sha512", "sha1", "md5",
    "aes-256-gcm", "aes-128-gcm", "aes-256-cbc", "aes-128-cbc",
    "RSA-OAEP", "AES-GCM", "AES-CBC", "PBKDF2", "HMAC",
    "bcrypt", "argon2",
]


def _match_known_algorithm(line: str) -> Optional[str]:
    for algo in KNOWN_ALGORITHMS:
        if algo in line:
            return algo
    return None


def _first_string_argument(line: str, function: str) -> Optional[str]:
    match = re.search(rf"{re.escape(function)}\s*\(\s*['\"]([^'\"]+)['\"]", line)
    if match:
        return clean_algorithm_text(match.group(1))
    return None


def detect(file_path: str, lines: List[str]) -> List[Dict[str, Any]]:
    language = detect_language(file_path) or "javascript"

    findings: List[Dict[str, Any]] = []

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith("//") or line.startswith("*"):
            continue

        for func, operation in NODE_CRYPTO_FUNCS.items():
            if f"crypto.{func}(" not in line:
                continue

            algorithm = _first_string_argument(line, func)
            if algorithm is None:
                algorithm = _match_known_algorithm(line)

            confidence = "HIGH" if algorithm else "MEDIUM"

            findings.append(
                make_finding(
                    algorithm=algorithm,
                    operation=operation,
                    language=language,
                    library="node:crypto",
                    api=f"crypto.{func}",
                    file_path=file_path,
                    line_number=line_no,
                    evidence=build_snippet(lines, line_no),
                    confidence=confidence,
                )
            )
            break

        for method, operation in WEB_CRYPTO_SUBTLE_FUNCS.items():
            if f"subtle.{method}(" not in line:
                continue

            algorithm = _first_string_argument(line, method)
            if algorithm is None:
                algorithm = _match_known_algorithm(line)

            confidence = "HIGH" if algorithm else "MEDIUM"

            findings.append(
                make_finding(
                    algorithm=algorithm,
                    operation=operation,
                    language=language,
                    library="Web Crypto API",
                    api=f"crypto.subtle.{method}",
                    file_path=file_path,
                    line_number=line_no,
                    evidence=build_snippet(lines, line_no),
                    confidence=confidence,
                )
            )
            break

        if not any(f["line_number"] == line_no for f in findings):
            if re.search(r"(require\(['\"]crypto['\"]\)|from ['\"]crypto['\"]|node:crypto)", line):
                findings.append(
                    make_finding(
                        algorithm=None,
                        operation="crypto_import",
                        language=language,
                        library="node:crypto",
                        api="crypto (import)",
                        file_path=file_path,
                        line_number=line_no,
                        evidence=build_snippet(lines, line_no),
                        confidence="LOW",
                    )
                )

    return findings