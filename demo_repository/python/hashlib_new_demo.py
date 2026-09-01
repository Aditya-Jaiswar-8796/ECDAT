# demo_repository/python/hashlib_new_demo.py
#
# SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
# SIH presentation. Never run in production.

import hashlib


def sha512_digest(data: bytes) -> bytes:
    """Compute a SHA-512 digest using hashlib.new (demo only)."""
    # <-- scanner detects this line: hashlib.new('sha512')
    hasher = hashlib.new("sha512")
    hasher.update(data)
    return hasher.digest()