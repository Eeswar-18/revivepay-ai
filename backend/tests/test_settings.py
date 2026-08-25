"""
tests/test_settings.py — Tests for Settings validation.
"""

from __future__ import annotations

import os

import pytest

from app.config import Settings, get_settings


def test_settings_mock_provider_requires_no_key() -> None:
    """LLM_PROVIDER=mock works without any API key."""
    s = Settings(
        DATABASE_URL="sqlite:///:memory:",
        LLM_PROVIDER="mock",
        GEMINI_API_KEY="",
        OPENAI_API_KEY="",
        ANTHROPIC_API_KEY="",
    )
    assert s.LLM_PROVIDER == "mock"


def test_settings_openai_fails_without_key() -> None:
    """Settings validation fails fast when LLM_PROVIDER=openai and OPENAI_API_KEY is absent."""
    with pytest.raises(Exception, match="OPENAI_API_KEY"):
        Settings(
            DATABASE_URL="sqlite:///:memory:",
            LLM_PROVIDER="openai",
            OPENAI_API_KEY="",
            GEMINI_API_KEY="",
            ANTHROPIC_API_KEY="",
        )


def test_settings_gemini_fails_without_key() -> None:
    """Settings validation fails fast when LLM_PROVIDER=gemini and GEMINI_API_KEY is absent."""
    with pytest.raises(Exception, match="GEMINI_API_KEY"):
        Settings(
            DATABASE_URL="sqlite:///:memory:",
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="",
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
        )


def test_settings_anthropic_fails_without_key() -> None:
    """Settings validation fails fast when LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY is absent."""
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        Settings(
            DATABASE_URL="sqlite:///:memory:",
            LLM_PROVIDER="anthropic",
            GEMINI_API_KEY="",
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
        )


def test_settings_openai_succeeds_with_key() -> None:
    """Settings validation passes when LLM_PROVIDER=openai and OPENAI_API_KEY is set."""
    s = Settings(
        DATABASE_URL="sqlite:///:memory:",
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test-fake-key-for-testing",
        GEMINI_API_KEY="",
        ANTHROPIC_API_KEY="",
    )
    assert s.LLM_PROVIDER == "openai"


def test_settings_default_seed() -> None:
    """SIM_DEFAULT_SEED has a fixed integer default for reproducibility."""
    s = Settings(DATABASE_URL="sqlite:///:memory:", LLM_PROVIDER="mock")
    assert isinstance(s.SIM_DEFAULT_SEED, int)
    assert s.SIM_DEFAULT_SEED == 42


def test_get_settings_is_cached() -> None:
    """get_settings() returns the same instance on repeated calls."""
    get_settings.cache_clear()
    # Must override DATABASE_URL in env to avoid missing dir issues in CI.
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    try:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
    finally:
        get_settings.cache_clear()
        if original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_url


def test_redacted_summary_hides_secrets() -> None:
    """redacted_summary() replaces all secret values with 'set' or 'unset'."""
    s = Settings(
        DATABASE_URL="sqlite:///:memory:",
        LLM_PROVIDER="mock",
        API_KEY_OPERATOR="my-very-secret-operator-key",
        API_KEY_VIEWER="my-very-secret-viewer-key",
        GEMINI_API_KEY="",
        OPENAI_API_KEY="",
        ANTHROPIC_API_KEY="",
    )
    summary = s.redacted_summary()

    assert summary["API_KEY_OPERATOR"] == "set"
    assert summary["API_KEY_VIEWER"] == "set"
    assert summary["GEMINI_API_KEY"] == "unset"

    # The raw values must not appear.
    import json

    body = json.dumps(summary)
    assert "my-very-secret-operator-key" not in body
    assert "my-very-secret-viewer-key" not in body
