"""Recommendation schema.

A remediation recommendation produced by Member 5 for a given crypto asset
(or a scan wide migration plan). Includes the concrete suggestion and an
explanatory note for the dashboard.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    """A single remediation / migration recommendation."""

    scan_id: Optional[str] = None
    asset_id: Optional[str] = None
    recommendation: str
    explanation: Optional[str] = None

    # Optional supporting suggested migration target (e.g. algorithm name).
    suggested_target: Optional[str] = None
    effort_estimate: Optional[str] = None

    model_config = {"from_attributes": True}
