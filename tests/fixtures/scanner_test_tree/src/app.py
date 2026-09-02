// tests/fixtures/scanner_test_tree/src/app.py
import hashlib

# This file is inside an ignored directory "node_modules",
# which is one level below src - it should never be scanned.
def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()