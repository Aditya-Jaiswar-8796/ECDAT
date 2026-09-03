from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base import make_finding
from ..evidence import build_snippet, clean_algorithm_text, extract_arguments


API_OPERATIONS: Dict[str, str] = {
    "Cipher.getInstance": ("javax.crypto", "encryption"),
    "Cipher": ("javax.crypto", "encryption"),
    "MessageDigest.getInstance": ("java.security", "hashing"),
    "MessageDigest": ("java.security", "hashing"),
    "KeyPairGenerator.getInstance": ("java.security", "key_generation"),
    "KeyGenerator.getInstance": ("javax.crypto", "key_generation"),
    "SecretKeyFactory.getInstance": ("javax.crypto", "key_derivation"),
    "Mac.getInstance": ("javax.crypto", "mac"),
    "Signature.getInstance": ("java.security", "signature"),
    "SecureRandom": ("java.security", "randomness"),
    "KeyStore": ("java.security", "keystore"),
    "KeyAgreement.getInstance": ("javax.crypto", "key_agreement"),
}

WEAK_LIBRARY_IMPORTS: List[str] = [
    "javax.crypto",
    "java.security",
]

KNOWN_ALGORITHMS: List[str] = [
    "AES", "AES/GCM/NoPadding", "AES/CBC/PKCS5Padding",
    "RSA", "RSA/ECB/OAEPWithSHA-256AndMGF1Padding", "RSA/ECB/PKCS1Padding",
    "SHA-256", "SHA-1", "MD5", "SHA-384", "SHA-512",
    "PBEWithHmacSHA256AndAES_128", "EC", "ECDSA",
    "HmacSHA256", "HmacSHA1", "PBKDF2WithHmacSHA256",
    "DES", "DESede", "Blowfish",
]


def _normalize_algorithm(raw_algorithm: Optional[str]) -> Optional[str]:
    if not raw_algorithm:
        return None
    cleaned = clean_algorithm_text(raw_algorithm)
    if not cleaned:
        return None
    if "/" in cleaned:
        cleaned = cleaned.split("/")[0]
    return cleaned


def _match_known_algorithm(text: str) -> Optional[str]:
    for algo in KNOWN_ALGORITHMS:
        if algo in text:
            return algo
    return None


def detect(file_path: str, lines: List[str]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    # Remembers which APIs were already reported on the current line so we
    # don't emit duplicate findings or scan them repeatedly.
    line_seen: set[str] = set()

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.lstrip().startswith("//") or line.startswith("*"):
            continue

        line_findings: List[Dict[str, Any]] = []
        for pattern, (library, operation) in API_OPERATIONS.items():
            if pattern not in line or pattern in line_seen:
                continue

            algorithm: Optional[str] = None
            confidence: str = "MEDIUM"

            if ".getInstance" in pattern and "(" in line:
                arg_text = extract_arguments(line, "getInstance")
                if arg_text:
                    first_arg = arg_text.split(",")[0]
                    raw_algo = _match_known_algorithm(first_arg) or first_arg
                    algorithm = _normalize_algorithm(raw_algo)

            if algorithm is None:
                algorithm = _normalize_algorithm(_match_known_algorithm(line))

            if algorithm:
                confidence = "HIGH"

            evidence_block = build_snippet(lines, line_no)

            line_findings.append(
                make_finding(
                    algorithm=algorithm,
                    operation=operation,
                    language="java",
                    library=library,
                    api=pattern,
                    file_path=file_path,
                    line_number=line_no,
                    evidence=evidence_block,
                    confidence=confidence,
                )
            )
            line_seen.add(pattern)

        if line_findings:
            # Keep the most specific (longest) API match for this line.
            keep = max(line_findings, key=lambda f: len(f["api"]))
            findings.append(keep)

    return findings