"""
app/db.py — SQLAlchemy 2.0 synchronous engine, session factory, and FastAPI dependency.

Design notes:
- Synchronous engine is used in Phase 1 (health/version/config only).
  Async migration (aiosqlite + AsyncSession) is planned for Phase 2 when
  domain endpoints with real IO appear. See ADR-0009 in DECISIONS.md.
- All SQLite pragmas are applied via an event listener on connect — they are
  functionally equivalent on PostgreSQL (WAL is the default, foreign_keys
  is a no-op, busy_timeout maps to lock_timeout). No raw SQL outside this file.
- No ORM entities are defined here. Phase 2 will add them in app/models/.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM entity definitions.

    Phases 2+ will import this Base and define their models as subclasses.
    """


def _apply_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:  # noqa: ANN401
    """Apply SQLite connection-level pragmas.

    Called by SQLAlchemy's ``connect`` event every time a new low-level
    DBAPI connection is created from the pool.

    These settings are safe to apply even when the DATABASE_URL points at
    PostgreSQL — SQLAlchemy's event only fires for SQLite connections.
    """
    _ = connection_record  # unused but required by the event signature
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def _build_engine(database_url: str) -> Engine:
    """Create and configure a SQLAlchemy engine for the given URL."""
    engine = create_engine(
        database_url,
        # pool_pre_ping avoids stale connections in long-lived processes.
        pool_pre_ping=True,
        # echo=False in all environments; structured request logs cover tracing.
        echo=False,
    )
    # Apply SQLite pragmas on every new connection from the pool.
    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _apply_sqlite_pragmas)
    return engine


def _get_engine() -> Engine:
    """Return the application-level engine, built from current settings."""
    return _build_engine(get_settings().DATABASE_URL)


# Module-level session factory; tests override this via dependency injection.
_SessionLocal: sessionmaker[Session] | None = None


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return the module-level sessionmaker, creating it on first use."""
    global _SessionLocal  # noqa: PLW0603
    if _SessionLocal is None or engine is not None:
        resolved_engine = engine if engine is not None else _get_engine()
        _SessionLocal = sessionmaker(
            bind=resolved_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Commits on clean exit, rolls back on any exception, and always closes
    the session so the connection is returned to the pool.

    Usage::

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    factory = get_session_factory()
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db(engine: Engine | None = None) -> None:
    """Create all tables registered on Base.metadata.

    Idempotent — safe to call on every startup. In Phase 1 this creates
    an empty schema because no models are defined yet; later phases add
    entities by subclassing Base.
    """
    resolved_engine = engine if engine is not None else _get_engine()
    Base.metadata.create_all(bind=resolved_engine)


def check_db_health(engine: Engine | None = None) -> bool:
    """Return True if the database responds to a trivial query, False otherwise."""
    try:
        resolved_engine = engine if engine is not None else _get_engine()
        with resolved_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
