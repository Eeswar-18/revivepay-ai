"""
app/config — Application configuration and agent-visible economics config.

This package provides:
- ``Settings`` and ``get_settings``: pydantic-settings application config,
  re-exported from ``app.config.settings`` so that all existing
  ``from app.config import get_settings`` imports continue to work unchanged.
- ``app/config/economics.yaml``: agent-visible economics parameters (MDR,
  intervention costs, segment LTV/churn estimates).  Readable by any layer
  including decision code.  Must never import from ``app.sim``.
"""

from app.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
