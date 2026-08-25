"""
app/core/banding.py — Amount-band utility for the RevivePay AI decision pipeline.

Maps an integer paise amount to a named band string.  The thresholds are
hard-coded module constants that mirror the ``amount_bands`` keys in
``backend/app/sim/world_config.yaml``.  They represent observable business
facts (e.g. "a micro-transaction is anything under Rs 100") rather than
hidden ground-truth parameters, so decision code is allowed to import and
use them freely.

This module must not import anything from ``app.sim``.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Band thresholds (integer paise, inclusive upper bound except XLARGE).
# These mirror the amount_bands keys in world_config.yaml and represent
# observable business facts, not held-out ground truth.
# ---------------------------------------------------------------------------
_MICRO_MAX: int = 10_000      # up to and including Rs 100 (10 000 paise)
_SMALL_MAX: int = 100_000     # up to and including Rs 1 000
_MEDIUM_MAX: int = 1_000_000  # up to and including Rs 10 000
_LARGE_MAX: int = 5_000_000   # up to and including Rs 50 000
# XLARGE: anything strictly above _LARGE_MAX


def amount_band_for(amount_minor: int) -> str:
    """Return the band name for *amount_minor* paise.

    Parameters
    ----------
    amount_minor:
        Transaction amount expressed as an integer number of paise.
        Must be non-negative.

    Returns
    -------
    str
        One of ``"MICRO"``, ``"SMALL"``, ``"MEDIUM"``, ``"LARGE"``,
        ``"XLARGE"``.

    Raises
    ------
    ValueError
        If *amount_minor* is negative.
    """
    if amount_minor < 0:
        raise ValueError(
            f"amount_minor must be non-negative; got {amount_minor}"
        )
    if amount_minor <= _MICRO_MAX:
        return "MICRO"
    if amount_minor <= _SMALL_MAX:
        return "SMALL"
    if amount_minor <= _MEDIUM_MAX:
        return "MEDIUM"
    if amount_minor <= _LARGE_MAX:
        return "LARGE"
    return "XLARGE"
