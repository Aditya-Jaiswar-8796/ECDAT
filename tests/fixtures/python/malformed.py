# tests/fixtures/python/malformed.py
# Deliberately broken Python that still contains a crypto call.
def broken(
    value = [1, 2
    digest = hashlib.md5(value)   # md5 usage
    return digest