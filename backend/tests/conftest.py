"""Pytest bootstrap: make the backend package importable from anywhere.

Tests live in backend/tests and import the `app` package. Inserting the backend
directory on sys.path makes `python -m pytest` and bare `pytest` both work
regardless of the invocation directory.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))