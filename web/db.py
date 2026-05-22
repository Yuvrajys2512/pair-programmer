"""SQLAlchemy engine + session factory for the web layer."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


_DB_PATH = Path(os.getenv("PAIRPROG_DB", str(Path(__file__).parent.parent / "pairprog.db")))
_DB_URL = f"sqlite:///{_DB_PATH.as_posix()}"

engine = create_engine(
    _DB_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables if they don't exist. Idempotent."""
    from web import storage  # noqa: F401 — register models on Base.metadata
    Base.metadata.create_all(engine)
