# demo_repository/python/token_encryptor.py
#
# SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
# SIH presentation. Never run in production.

from cryptography.fernet import Fernet

# <-- scanner detects this line: Fernet (AES-based symmetric encryption)
key = Fernet.generate_key()
fernet = Fernet(key)


def encrypt_token(token: str) -> bytes:
    """Encrypt a session token with Fernet (AES-128-CBC)."""
    return fernet.encrypt(token.encode("utf-8"))


def decrypt_token(token_bytes: bytes) -> str:
    """Decrypt a Fernet token back to its original string."""
    return fernet.decrypt(token_bytes).decode("utf-8")