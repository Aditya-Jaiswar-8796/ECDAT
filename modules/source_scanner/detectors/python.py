from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base import make_finding
from ..evidence import build_snippet, clean_algorithm_text

HASHLIB_FUNCS: Dict[str, str] = {
    "sha256": "SHA-256",
    "sha512": "SHA-512",
    "sha1": "SHA-1",
    "md5": "MD5",
    "sha224": "SHA-224",
    "sha384": "SHA-384",
    "blake2b": "BLAKE2b",
    "blake2s": "BLAKE2s",
    "sha3_256": "SHA3-256",
    "sha3_512": "SHA3-512",
}

STANDALONE_PATTERNS: Dict[str, str] = {
    "hmac.new": ("hmac", "mac"),
    "os.urandom": ("os", "randomness"),
    "secrets.token_hex": ("secrets", "randomness"),
    "secrets.token_bytes": ("secrets", "randomness"),
}

HASHLIB_NEW_ALGORITHMS: List[str] = [
    "sha256", "sha512", "sha1", "md5", "sha224", "sha384",
    "blake2b", "blake2s", "sha3_256", "sha3_512",
]


def _normalize_hash_algorithm(name: str) -> str:
    return HASHLIB_FUNCS.get(name, name)


def _match_hashlib_function(line: str) -> Optional[str]:
    for func in HASHLIB_FUNCS:
        if f"hashlib.{func}(" in line:
            return func
    return None


def _match_hashlib_new(line: str) -> Optional[str]:
    match = re.search(r"hashlib\.new\(\s*['\"]([^'\"]+)['\"]", line)
    if match:
        candidate = clean_algorithm_text(match.group(1))
        if candidate in HASHLIB_NEW_ALGORITHMS:
            return candidate
    return None


def _match_fernet(line: str) -> Optional[str]:
    if "Fernet" not in line:
        return None
    if ("import Fernet" in line
            or "Fernet(" in line
            or "Fernet.generate_key" in line):
        return "AES-128-CBC (Fernet)"
    return None


def detect(file_path: str, lines: List[str]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.lstrip().startswith("#"):
            continue

        algorithm: Optional[str] = None
        api: Optional[str] = None
        library: str = "hashlib"
        operation: str = "hashing"
        confidence: str = "MEDIUM"

        func = _match_hashlib_function(line)
        if func:
            api = f"hashlib.{func}"
            algorithm = _normalize_hash_algorithm(func)
            confidence = "HIGH"

        if api is None:
            new_algo = _match_hashlib_new(line)
            if new_algo:
                api = "hashlib.new"
                algorithm = _normalize_hash_algorithm(new_algo)
                confidence = "HIGH"

        if api is None and "hashlib.pbkdf2_hmac" in line:
            api = "hashlib.pbkdf2_hmac"
            library = "hashlib"
            operation = "key_derivation"
            algorithm = "PBKDF2"
            confidence = "MEDIUM"

        if api is None:
            fernet_algo = _match_fernet(line)
            if fernet_algo:
                api = "cryptography.fernet.Fernet"
                library = "cryptography"
                operation = "symmetric_encryption"
                algorithm = fernet_algo
                confidence = "MEDIUM"

        if api is None:
            for pattern, (pattern_library, pattern_op) in STANDALONE_PATTERNS.items():
                if pattern in line:
                    api = pattern
                    library = pattern_library
                    operation = pattern_op
                    algorithm = None
                    confidence = "MEDIUM"
                    break

        if api is None:
            continue

        evidence_block = build_snippet(lines, line_no)
        findings.append(
            make_finding(
                algorithm=algorithm,
                operation=operation,
                language="python",
                library=library,
                api=api,
                file_path=file_path,
                line_number=line_no,
                evidence=evidence_block,
                confidence=confidence,
            )
        )

    return findings