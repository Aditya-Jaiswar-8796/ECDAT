from __future__ import annotations

from typing import Any, Dict, Optional

from ..confidence import validate_confidence


def make_finding(
    algorithm: Optional[str],
    operation: str,
    language: str,
    library: str,
    api: str,
    file_path: str,
    line_number: int,
    evidence: str,
    confidence: str,
) -> Dict[str, Any]:
    return {
        "id": None,
        "algorithm": algorithm,
        "operation": operation,
        "key_size": None,
        "language": language,
        "library": library,
        "api": api,
        "file_path": file_path,
        "line_number": line_number,
        "evidence": evidence,
        "confidence": validate_confidence(confidence),
        "business_criticality": None,
        "data_lifetime_years": None,
        "internet_exposure": None,
        "migration_complexity": None,
        "risk_score": None,
        "risk_level": None,
        "migration_priority": None,
        "mosca_assessment": None,
        "recommendation": None,
    }