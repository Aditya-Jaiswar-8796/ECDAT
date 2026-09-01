"""Health endpoint.

Used for liveness checks by Member 6 (dashboard) and any orchestrator, plus a
light DB connectivity probe.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Report service health and database connectivity."""
    db_ok = True
    try:
        # Cheap round-trip to prove the SQLite store is reachable.
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}