"""
tests/conftest.py — Shared pytest fixtures.

Provides:
- A temporary SQLite database (one per test session, in a temp directory).
- A FastAPI TestClient bound to an isolated settings instance that uses that DB.
- Overridden get_db() and get_settings() dependencies so the app never touches
  the real database or reads production environment variables during tests.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Register all ORM models on Base.metadata before init_db / create_all.
import app.models  # noqa: F401
from app.config import Settings, get_settings
from app.db import get_db, init_db
from app.main import create_app


@pytest.fixture(scope="session")
def test_db_url() -> Generator[str, None, None]:
    """Yield a temporary SQLite database URL for the test session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_revivepay.db")
        yield f"sqlite:///{db_path}"


@pytest.fixture(scope="session")
def test_engine(test_db_url: str) -> Generator[Engine, None, None]:
    """Create and yield a SQLAlchemy engine for the test database."""
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    init_db(engine=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_settings(test_db_url: str) -> Settings:
    """Return a Settings instance configured for tests.

    Uses a temp SQLite URL and mock LLM provider; clears the get_settings cache.
    """
    get_settings.cache_clear()
    settings = Settings(
        DATABASE_URL=test_db_url,
        LLM_PROVIDER="mock",
        APP_ENV="test",
        LOG_LEVEL="WARNING",
        API_KEY_OPERATOR="test-operator-key",
        API_KEY_VIEWER="test-viewer-key",
        GEMINI_API_KEY="",
        OPENAI_API_KEY="",
        ANTHROPIC_API_KEY="",
        RAZORPAY_KEY_ID="",
        RAZORPAY_KEY_SECRET="",
        FRONTEND_ORIGIN="http://localhost:3000",
    )
    return settings


@pytest.fixture(scope="session")
def client(test_engine: Engine, test_settings: Settings) -> Generator[TestClient, None, None]:
    """Yield a TestClient whose database and settings dependencies are isolated."""
    # Build a session factory bound to the test engine.
    TestingSessionLocal = sessionmaker(  # noqa: N806
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    def _override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _override_get_settings() -> Settings:
        return test_settings

    test_app = create_app(settings=test_settings)
    test_app.dependency_overrides[get_db] = _override_get_db
    test_app.dependency_overrides[get_settings] = _override_get_settings

    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c
