"""Cryptographic relevance detection for software dependencies.

Identifies packages that are likely related to cryptography, TLS/SSL,
hashing, signing, or other security-sensitive operations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class CryptoRelevance:
    """Result of cryptographic relevance analysis for a dependency."""
    is_relevant: bool
    confidence: str  # "high", "medium", "low"
    reasons: List[str] = field(default_factory=list)
    crypto_category: Optional[str] = None  # e.g. "hashing", "tls", "signing", "encryption"


# Known crypto-related packages mapped by ecosystem
# Each key is a dependency name (lowercase), value is CryptoRelevance info
_CRYPTO_PACKAGES: Dict[str, Dict[str, str]] = {
    # Python crypto packages
    "cryptography": {"confidence": "high", "category": "encryption"},
    "pyca": {"confidence": "high", "category": "encryption"},
    "pyopenssl": {"confidence": "high", "category": "tls"},
    "paramiko": {"confidence": "high", "category": "tls"},
    "bcrypt": {"confidence": "high", "category": "hashing"},
    "argon2-cffi": {"confidence": "high", "category": "hashing"},
    "passlib": {"confidence": "high", "category": "hashing"},
    "pycryptodome": {"confidence": "high", "category": "encryption"},
    "pycryptodomex": {"confidence": "high", "category": "encryption"},
    "pynacl": {"confidence": "high", "category": "encryption"},
    "nacl": {"confidence": "high", "category": "encryption"},
    "ecdsa": {"confidence": "high", "category": "signing"},
    "rsa": {"confidence": "high", "category": "signing"},
    "pyjwt": {"confidence": "high", "category": "signing"},
    "jose": {"confidence": "high", "category": "signing"},
    "jwcrypto": {"confidence": "high", "category": "signing"},
    "certifi": {"confidence": "medium", "category": "tls"},
    "certvalidator": {"confidence": "medium", "category": "tls"},
    "tls": {"confidence": "high", "category": "tls"},
    "ssl": {"confidence": "high", "category": "tls"},
    "hashlib": {"confidence": "medium", "category": "hashing"},
    "hmac": {"confidence": "medium", "category": "hashing"},
    "secrets": {"confidence": "medium", "category": "random_generation"},
    "requests-oauthlib": {"confidence": "medium", "category": "signing"},
    "oauthlib": {"confidence": "medium", "category": "signing"},
    "authlib": {"confidence": "high", "category": "signing"},
    "python-jose": {"confidence": "high", "category": "signing"},
    "crypto": {"confidence": "high", "category": "encryption"},
    "hsm": {"confidence": "high", "category": "hardware_security"},
    "pkcs11": {"confidence": "high", "category": "hardware_security"},
    # JavaScript/Node crypto packages
    "crypto-js": {"confidence": "high", "category": "encryption"},
    "crypto": {"confidence": "high", "category": "encryption"},
    "node-forge": {"confidence": "high", "category": "encryption"},
    "forge": {"confidence": "high", "category": "encryption"},
    "jose": {"confidence": "high", "category": "signing"},
    "jsonwebtoken": {"confidence": "high", "category": "signing"},
    "jws": {"confidence": "high", "category": "signing"},
    "passport-jwt": {"confidence": "high", "category": "signing"},
    "passport-local": {"confidence": "medium", "category": "authentication"},
    "bcryptjs": {"confidence": "high", "category": "hashing"},
    "scrypt": {"confidence": "high", "category": "hashing"},
    "tweetnacl": {"confidence": "high", "category": "encryption"},
    "tweetnacl-js": {"confidence": "high", "category": "encryption"},
    "elliptic": {"confidence": "high", "category": "signing"},
    "secp256k1": {"confidence": "high", "category": "signing"},
    "node-rsa": {"confidence": "high", "category": "signing"},
    "ursa": {"confidence": "high", "category": "signing"},
    "tls-js": {"confidence": "high", "category": "tls"},
    "https-proxy-agent": {"confidence": "low", "category": "tls"},
    "ssl-lock": {"confidence": "medium", "category": "tls"},
    # Java crypto packages
    "bouncycastle": {"confidence": "high", "category": "encryption"},
    "bcprov": {"confidence": "high", "category": "encryption"},
    "bcpkix": {"confidence": "high", "category": "encryption"},
    "bcmail": {"confidence": "high", "category": "encryption"},
    "bcpg": {"confidence": "high", "category": "signing"},
    "javax.crypto": {"confidence": "high", "category": "encryption"},
    "java.security": {"confidence": "high", "category": "encryption"},
    "spring-security-crypto": {"confidence": "high", "category": "hashing"},
    "jasypt": {"confidence": "high", "category": "encryption"},
    "keycloak": {"confidence": "medium", "category": "authentication"},
}

# Keyword patterns that suggest cryptographic relevance
_CRYPTO_KEYWORDS: List[Dict[str, str]] = [
    {"pattern": "crypto", "confidence": "high", "category": "encryption"},
    {"pattern": "cipher", "confidence": "high", "category": "encryption"},
    {"pattern": "encrypt", "confidence": "high", "category": "encryption"},
    {"pattern": "decrypt", "confidence": "high", "category": "encryption"},
    {"pattern": "hash", "confidence": "medium", "category": "hashing"},
    {"pattern": "hmac", "confidence": "high", "category": "hashing"},
    {"pattern": "signing", "confidence": "high", "category": "signing"},
    {"pattern": "signature", "confidence": "high", "category": "signing"},
    {"pattern": "certificate", "confidence": "medium", "category": "tls"},
    {"pattern": "ssl", "confidence": "high", "category": "tls"},
    {"pattern": "tls", "confidence": "high", "category": "tls"},
    {"pattern": "key-exchange", "confidence": "high", "category": "tls"},
    {"pattern": "jwt", "confidence": "high", "category": "signing"},
    {"pattern": "oauth", "confidence": "medium", "category": "signing"},
    {"pattern": "token", "confidence": "low", "category": "signing"},
    {"pattern": "pbkdf", "confidence": "high", "category": "hashing"},
    {"pattern": "argon", "confidence": "high", "category": "hashing"},
    {"pattern": "scrypt", "confidence": "high", "category": "hashing"},
    {"pattern": "bcrypt", "confidence": "high", "category": "hashing"},
    {"pattern": "ed25519", "confidence": "high", "category": "signing"},
    {"pattern": "ecdsa", "confidence": "high", "category": "signing"},
    {"pattern": "rsa", "confidence": "high", "category": "signing"},
    {"pattern": "dsa", "confidence": "high", "category": "signing"},
    {"pattern": "hsm", "confidence": "high", "category": "hardware_security"},
    {"pattern": "pkcs", "confidence": "high", "category": "encryption"},
    {"pattern": "pem", "confidence": "medium", "category": "tls"},
    {"pattern": "x509", "confidence": "medium", "category": "tls"},
    {"pattern": "keystore", "confidence": "medium", "category": "encryption"},
    {"pattern": "truststore", "confidence": "medium", "category": "tls"},
]


def check_crypto_relevance(name: str, description: str = "") -> CryptoRelevance:
    """Determine if a dependency is cryptographically relevant.

    Checks against known crypto packages first, then falls back to
    keyword-based heuristic matching on the package name and description.

    Args:
        name: The dependency name.
        description: Optional package description for richer matching.

    Returns:
        CryptoRelevance with relevance flag, confidence, reasons, and category.
    """
    reasons: List[str] = []
    name_lower = name.lower().strip()
    desc_lower = description.lower().strip()
    best_confidence: Optional[str] = None
    category: Optional[str] = None

    # Check against known crypto packages database
    if name_lower in _CRYPTO_PACKAGES:
        pkg_info = _CRYPTO_PACKAGES[name_lower]
        reasons.append(f"Known cryptographic package: {name}")
        best_confidence = pkg_info["confidence"]
        category = pkg_info["category"]

    # Also check suffix/prefix patterns (e.g. "pycrypto" matches "crypto")
    for pkg_name, pkg_info in _CRYPTO_PACKAGES.items():
        if pkg_name in name_lower and pkg_name != name_lower:
            reasons.append(f"Name contains known crypto package reference: {pkg_name}")
            if _confidence_rank(pkg_info["confidence"]) > _confidence_rank(best_confidence or "low"):
                best_confidence = pkg_info["confidence"]
                category = pkg_info["category"]

    # Keyword-based heuristic matching
    combined_text = f"{name_lower} {desc_lower}"
    for kw in _CRYPTO_KEYWORDS:
        if kw["pattern"] in combined_text:
            reason_text = f"Name/description contains crypto keyword: '{kw['pattern']}'"
            if reason_text not in reasons:
                reasons.append(reason_text)
            if _confidence_rank(kw["confidence"]) > _confidence_rank(best_confidence or "low"):
                best_confidence = kw["confidence"]
                category = kw["category"]

    is_relevant = len(reasons) > 0
    final_confidence = best_confidence if best_confidence else "low"

    return CryptoRelevance(
        is_relevant=is_relevant,
        confidence=final_confidence,
        reasons=reasons,
        crypto_category=category,
    )


def _confidence_rank(confidence: str) -> int:
    """Map confidence string to numeric rank for comparison."""
    return {"high": 3, "medium": 2, "low": 1}.get(confidence, 0)
