# tests/fixtures/python/crypto_app.py
import hashlib
import hmac
import os


def sha512(data: bytes) -> bytes:
    # direct hashlib function call
    return hashlib.sha512(data).digest()


def new_sha1(data: bytes) -> bytes:
    # hashlib.new style call
    h = hashlib.new("sha1")
    h.update(data)
    return h.digest()


def mac(secret: bytes, msg: bytes) -> bytes:
    # hmac usage
    return hmac.new(secret, msg, hashlib.sha256).digest()


def random_bytes(n: int) -> bytes:
    # os.urandom (randomness, weak signal)
    return os.urandom(n)