# demo_repository/python/password_hasher.py
#
# SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
# SIH presentation. Never run in production.

import hashlib
import hmac


def hash_password(password: str, salt: bytes) -> str:
    """Compute a salted SHA-256 hash of a password (demo only)."""
    # <-- scanner detects this line: hashlib.sha256
    digest = hashlib.sha256(salt + password.encode("utf-8"))
    return digest.hexdigest()


def sign_message(secret: bytes, message: str) -> str:
    """Create an HMAC tag over a message using a shared secret."""
    # <-- scanner detects this line: hmac.new
    return hmac.new(secret, message.encode("utf-8"), hashlib.sha256).hexdigest()