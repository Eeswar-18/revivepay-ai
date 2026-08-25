"""
app/models/policy_versions.py — Policy version models.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class PolicyVersion(Base):
    """A policy version."""

    __tablename__ = "policy_versions"

    version: Mapped[str] = mapped_column(String(50), primary_key=True)
    yaml_text: Mapped[str] = mapped_column(String)
    hash: Mapped[str] = mapped_column(String(64))
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str] = mapped_column(String)
