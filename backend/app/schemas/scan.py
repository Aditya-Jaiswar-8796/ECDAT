"""Scan lifecycle schema.

A Scan represents one submitted project/source bundle (typically a ZIP) that
gets processed by the pipeline. The scan tracks which stage of the pipeline
(Member 1 ingest -> Member 3 source scan -> Member 4 deps/certs/CBOM -> Member 5
risk) has completed and holds any pipeline error.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Lifecycle states for a scan as it flows through the integration pipeline.
ScanStatus = Literal[
    "RECEIVED",      # uploaded and persisted, awaiting source scan
    "SCANNING",      # source scan (Member 3) in progress
    "SCAN_COMPLETE", # source scan done, dependencies/certs/CBOM running
    "RISK_ASSESSED", # risk engine (Member 5) completed
    "FAILED",        # a pipeline stage raised an error
]


class ScanCreate(BaseModel):
    """Minimal metadata accepted when a scan is first created/uploaded."""

    name: str = Field(..., description="Human friendly scan name")
    project_name: Optional[str] = None
    language: Optional[str] = None


class Scan(ScanCreate):
    """Full scan record as returned by the API."""

    scan_id: str
    status: ScanStatus = "RECEIVED"
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None
    asset_count: int = 0
    dependency_count: int = 0
    certificate_count: int = 0

    model_config = {"from_attributes": True}
