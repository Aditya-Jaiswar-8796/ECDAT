# demo_repository/python/plain_math.py
#
# SAFE DEMO CODE - intentionally contains NO cryptographic usage.
# Used to demonstrate that the scanner correctly produces no findings
# for files with no crypto-related patterns.


def add(a: int, b: int) -> int:
    """Simple addition (no crypto anywhere)."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Simple multiplication (no crypto anywhere)."""
    return a * b


def fibonacci(n: int) -> int:
    """Classic non-crypto function."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)