"""SQLAlchemy engine + session factory for the web layer."""

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
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


# Additive migrations for SQLite — keyed by (table, column) → DDL fragment.
# create_all only adds new tables; this catches columns added to existing
# tables in later phases (e.g. Phase 9 added Review.persona).
_COLUMN_MIGRATIONS: dict[tuple[str, str], str] = {
    ("reviews", "persona"): "VARCHAR(64)",
}


def _apply_column_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for (table, column), ddl in _COLUMN_MIGRATIONS.items():
            if table not in existing_tables:
                continue
            cols = {c["name"] for c in inspector.get_columns(table)}
            if column in cols:
                continue
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {ddl}'))


def init_db() -> None:
    """Create tables if they don't exist, then run additive column migrations."""
    from web import storage  # noqa: F401 — register models on Base.metadata
    Base.metadata.create_all(engine)
    _apply_column_migrations()
