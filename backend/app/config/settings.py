"""
app/config.py — Application configuration using pydantic-settings.

All settings are loaded from environment variables and optionally a .env file.
No secret value is ever returned from redacted_summary(); see that method for details.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for all runtime configuration.

    Values are read from environment variables first, then from a .env file
    in the current working directory if one exists.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "test", "production"] = "development"
    APP_NAME: str = "RevivePay AI"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── API Server ───────────────────────────────────────────────────────────
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    # ── CORS ────────────────────────────────────────────────────────────────
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/revivepay.db"

    # ── API Authentication ───────────────────────────────────────────────────
    API_KEY_OPERATOR: str = "change-me-operator-key-placeholder"
    API_KEY_VIEWER: str = "change-me-viewer-key-placeholder"

    # ── LLM Provider ─────────────────────────────────────────────────────────
    LLM_PROVIDER: Literal["mock", "gemini", "openai", "anthropic"] = "mock"
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 3

    # ── LLM API Keys ─────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ── Policy and Config Files ───────────────────────────────────────────────
    POLICY_FILE: str = "app/core/policy/policy.yaml"
    ECON_CONFIG_FILE: str = "app/config/economics.yaml"

    # NOTE: there is deliberately NO WORLD_CONFIG_FILE setting.
    #
    # An earlier version exposed one, defaulting to the stale path
    # "app/core/environment/world_config.yaml" (the file actually lives at
    # app/sim/world_config.yaml). It was never read by any code, but it was a
    # boundary hazard on two counts: it is a decision-side, env-overridable
    # pointer at held-out ground truth, and a configurable path would let
    # anyone repoint the "pre-registered" world at a different file — which
    # would silently destroy the hash pre-registration claim that the whole
    # evaluation rests on.
    #
    # app.sim.environment resolves its config relative to its own __file__
    # instead. That path is not configurable, by design.

    # ── Simulation and Evaluation ─────────────────────────────────────────────
    SIM_DEFAULT_SEED: int = 42

    # ── Safety Controls ───────────────────────────────────────────────────────
    KILL_SWITCH_ENABLED: bool = False
    RATE_LIMIT_SIMULATION_PER_MIN: int = 60

    # ── Payment Adapter ───────────────────────────────────────────────────────
    RAZORPAY_ADAPTER_ENABLED: bool = False
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # ── Frontend ──────────────────────────────────────────────────────────────
    NEXT_PUBLIC_API_BASE_URL: str = "http://localhost:8000"
    NEXT_PUBLIC_DEMO_MODE: bool = True

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("DATABASE_URL")
    @classmethod
    def _ensure_db_parent_dir(cls, v: str) -> str:
        """Create the database file's parent directory if it does not exist."""
        if v.startswith("sqlite"):
            # Extract the file path portion after the scheme prefix.
            # Handles sqlite:///./path and sqlite:////abs/path.
            path_part = v.split("///", 1)[-1].lstrip("/")
            if path_part and path_part != ":memory:":
                # Normalise relative paths relative to the current working directory.
                db_path = Path(path_part)
                if not db_path.is_absolute():
                    db_path = Path(os.getcwd()) / db_path
                db_path.parent.mkdir(parents=True, exist_ok=True)
        return v

    @model_validator(mode="after")
    def _require_api_key_for_non_mock_provider(self) -> Settings:
        """Fail fast at startup if a non-mock provider is selected without its key."""
        provider = self.LLM_PROVIDER
        missing: str | None = None

        if provider == "gemini" and not self.GEMINI_API_KEY:
            missing = "GEMINI_API_KEY"
        elif provider == "openai" and not self.OPENAI_API_KEY:
            missing = "OPENAI_API_KEY"
        elif provider == "anthropic" and not self.ANTHROPIC_API_KEY:
            missing = "ANTHROPIC_API_KEY"

        if missing:
            raise ValueError(
                f"LLM_PROVIDER is set to '{provider}' but {missing} is not set. "
                f"Either set {missing} in your environment/.env file, "
                f"or set LLM_PROVIDER=mock to run without an API key."
            )
        return self

    # ── Secret-safe summary ───────────────────────────────────────────────────

    #: Names of fields whose values must never appear in logs or API responses.
    _SECRET_FIELDS: frozenset[str] = frozenset(
        {
            "API_KEY_OPERATOR",
            "API_KEY_VIEWER",
            "GEMINI_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "RAZORPAY_KEY_ID",
            "RAZORPAY_KEY_SECRET",
        }
    )

    def redacted_summary(self) -> dict[str, object]:
        """Return a dict of all settings safe for logging and the /api/system/config endpoint.

        Every secret field is replaced with the string "set" if a non-empty value is
        configured, or "unset" if it is empty. The raw value is never included.
        """
        result: dict[str, object] = {}
        for field_name in type(self).model_fields:
            value = getattr(self, field_name)
            if field_name in self._SECRET_FIELDS:
                result[field_name] = "set" if value else "unset"
            else:
                result[field_name] = value
        return result


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance.

    The cache is populated on first call. Call ``get_settings.cache_clear()``
    in tests to force re-instantiation with different environment variables.
    """
    return Settings()
