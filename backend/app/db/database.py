"""SQLite database boundary for the ECDAT backend.

Uses SQLAlchemy with SQLite as the backing store. For a hackathon prototype
this keeps things simple and dependency-free on external DB servers. The
database file lives in ./backend/app.db by default, overridable via the
ECDAT_DB_PATH environment variable (useful for tests).
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Default DB path relative to the backend/ package; overridable for tests.
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "app.db")
DB_PATH = os.getenv("ECDAT_DB_PATH", DEFAULT_DB_PATH)

# check_same_thread=False is required because FastAPI runs sync handle_method
# calls on a threadpool while the engine may be created on the main thread.
engine = create_engine(
    f"sqlite:///{os.path.abspath(DB_PATH)}",
    connect_args={"check_same_thread": False},
)

# A scoped session factory used by dependency-injected DB session handlers.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def get_db():
    """FastAPI dependency that yields a DB session and always closes it.

    Each request gets its own session, committed by the caller on success and
    closed here regardless of outcome.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they do not already exist.

    Called once at application startup so the SQLite schema is ready before
    the first request arrives.
    """
    from app.db import models  # noqa: F401  (register models on Base)

    Base.metadata.create_all(bind=engine)
