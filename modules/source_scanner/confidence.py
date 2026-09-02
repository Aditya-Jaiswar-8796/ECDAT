from __future__ import annotations

from typing import Optional

VALID_CONFIDENCE_LEVELS: tuple[str, ...] = ("HIGH", "MEDIUM", "LOW")


def assign_confidence(api: str, algorithm: Optional[str] = None) -> str:
    if not api:
        return "LOW"
    if algorithm:
        return "HIGH"
    return "MEDIUM"


def validate_confidence(value: str) -> str:
    if value in VALID_CONFIDENCE_LEVELS:
        return value
    return "LOW"