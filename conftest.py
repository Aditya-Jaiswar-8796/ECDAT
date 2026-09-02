"""Pytest fixtures and path setup for ECDAT tests."""

import os
import sys

# Ensure repository root is importable so that `modules` and `tests` packages work
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)