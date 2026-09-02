"""EC DAT - Post Quantum Readiness (SIH 26164) backend entrypoint.

Member 1 responsibility: FastAPI + SQLite + integration. This module wires
up the whole backend: DB init, CORS, routers and the canonical schemas.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_assets,
    routes_cbom,
    routes_health,
    routes_risk,
    routes_scan,
)
from app.db.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Ensure the SQLite schema exists before serving requests.
    init_db()
    yield


app = FastAPI(
    title="ECDAT - Post Quantum Readiness API",
    description=(
        "Central persistence + integration layer for the ECDAT crypto asset "
        "discovery pipeline. Consumes findings from source scanner (Member 3), "
        "dependency/certificate/CBOM analysis (Member 4) and the risk engine "
        "(Member 5); exposes stable APIs to the dashboard (Member 6)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the frontend (Member 6) to call these APIs from any origin in the
# hackathon prototype.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration per API area.
app.include_router(routes_health.router)
app.include_router(routes_scan.router)
app.include_router(routes_assets.router)
app.include_router(routes_risk.risks_router)
app.include_router(routes_risk.recommendations_router)
app.include_router(routes_cbom.router)

# Root endpoint so hitting / returns a minimal service banner.
@app.get("/", tags=["meta"])
def root():
    """Service banner for quick manual verification."""
    return {"service": "ECDAT backend", "docs": "/docs"}