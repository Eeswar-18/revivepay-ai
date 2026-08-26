"""
tests/test_taxonomy_alignment.py — Bind the domain enums to the pre-registered world.

``backend/app/sim/world_config.yaml`` is the hash-pre-registered source of
truth for every categorical dimension in this project.  The enums in
``app/models/enums.py`` mirror its keys as literals so that decision-side code
never has to read the held-out config in order to *name* things.

Mirroring introduces a drift risk, and that risk already materialised once:
``FailureClass`` and ``ActionType`` were written during Phase 1, before the
world config existed, and ended up sharing exactly ONE member with it.  Every
name the agent could emit was ungradeable by the environment.

These tests make that class of drift impossible to reintroduce.  They assert
**set bijections**, not merely subset relations, because both directions
matter:

* An enum member missing from the config is an action the agent can propose
  but the world cannot grade — the evaluation would contain cells with
  undefined outcomes and the reported uplift would not be falsifiable.
* A config key missing from the enum is a world behaviour the agent can never
  choose, which silently caps achievable performance and makes the oracle
  ceiling wrong.

This file is one of the few places outside ``app/sim/`` that may legitimately
read ``world_config.yaml``: it lives in ``tests/``, not ``app/``, and it reads
only the *keys*, never the ground-truth values.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.core.banding import amount_band_for
from app.models.enums import (
    ActionType,
    AmountBand,
    CustomerSegment,
    DelayBand,
    FailureClass,
    Rail,
)

_SIM_DIR = Path(__file__).resolve().parents[1] / "app" / "sim"
_WORLD_CONFIG_PATH = _SIM_DIR / "world_config.yaml"
_HASH_PATH = _SIM_DIR / "WORLD_CONFIG_HASH.txt"


@pytest.fixture(scope="module")
def world_config() -> dict[str, Any]:
    """The parsed pre-registered world configuration."""
    text = _WORLD_CONFIG_PATH.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)
    assert isinstance(parsed, dict), "world_config.yaml must parse to a mapping"
    return parsed


def _enum_values(enum_cls: type[Enum]) -> set[str]:
    return {str(member.value) for member in enum_cls}


# ---------------------------------------------------------------------------
# Pre-registration integrity
# ---------------------------------------------------------------------------


def test_world_config_still_matches_preregistered_hash() -> None:
    """The world config must be byte-for-byte what was committed before any agent existed.

    The hash is computed over NEWLINE-NORMALISED text, not raw bytes, so that
    a Windows checkout and a Linux CI runner agree even though git may
    translate line endings.

    This is the load-bearing claim of the whole evaluation: the environment
    that grades the agent was fixed *before* the agent was written, so the
    numbers cannot have been reverse-engineered from the world. If this test
    fails, either the config changed (and every previously reported metric is
    void) or the hash record was tampered with.
    """
    expected = _HASH_PATH.read_text(encoding="utf-8").strip()
    assert len(expected) == 64, f"expected a 64-char sha256, got {expected!r}"

    text = _WORLD_CONFIG_PATH.read_text(encoding="utf-8")
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    actual = hashlib.sha256(normalised.encode("utf-8")).hexdigest()

    assert actual == expected, (
        "world_config.yaml no longer matches its pre-registered hash.\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}\n"
        "If this change was intentional, the pre-registration claim is broken "
        "and every metric in reports/ must be regenerated and re-labelled."
    )


# ---------------------------------------------------------------------------
# Bijections between enums and world config keys
# ---------------------------------------------------------------------------


def test_failure_class_matches_world_config(world_config: dict[str, Any]) -> None:
    """FailureClass minus UNKNOWN must equal the failure_classes keys exactly."""
    config_keys = set(world_config["failure_classes"])
    enum_values = _enum_values(FailureClass) - {FailureClass.UNKNOWN.value}

    assert enum_values == config_keys, (
        "FailureClass has drifted from world_config.yaml:\n"
        f"  in enum only:   {sorted(enum_values - config_keys)}\n"
        f"  in config only: {sorted(config_keys - enum_values)}"
    )


def test_unknown_failure_class_is_not_a_world_key(world_config: dict[str, Any]) -> None:
    """UNKNOWN must be an agent-side concept only.

    It represents a gateway message the deterministic classifier could not
    map, giving the policy layer an explicit fail-closed branch. The world
    never produces it, so it must not appear as a config key — otherwise the
    exclusion in the test above would be silently hiding a real mismatch.
    """
    assert FailureClass.UNKNOWN.value not in world_config["failure_classes"]


def test_action_type_matches_world_interventions(world_config: dict[str, Any]) -> None:
    """The action space must equal the set of interventions the world can grade."""
    config_keys = set(world_config["interventions"])
    enum_values = _enum_values(ActionType)

    assert enum_values == config_keys, (
        "ActionType has drifted from world_config.yaml interventions:\n"
        f"  in enum only (ungradeable actions): {sorted(enum_values - config_keys)}\n"
        f"  in config only (unreachable):       {sorted(config_keys - enum_values)}"
    )


def test_delay_band_matches_world_config(world_config: dict[str, Any]) -> None:
    """DelayBand must equal the retry_delay_bands keys exactly."""
    config_keys = set(world_config["retry_delay_bands"])
    assert _enum_values(DelayBand) == config_keys


def test_customer_segment_matches_world_config(world_config: dict[str, Any]) -> None:
    """CustomerSegment must equal the customer_segments keys exactly."""
    config_keys = set(world_config["customer_segments"])
    assert _enum_values(CustomerSegment) == config_keys


def test_amount_band_matches_world_config(world_config: dict[str, Any]) -> None:
    """AmountBand must equal the amount_bands keys exactly."""
    config_keys = set(world_config["amount_bands"])
    assert _enum_values(AmountBand) == config_keys


def test_rail_matches_world_config(world_config: dict[str, Any]) -> None:
    """Rail must equal the ids of the rails LIST.

    Note the shape difference: ``rails`` is a list of ``{id, label, weight}``
    mappings, not a mapping keyed by rail name like every other section. A
    ``.keys()``-based check here would raise AttributeError rather than fail
    informatively.
    """
    rails = world_config["rails"]
    assert isinstance(rails, list), "rails is expected to be a list of mappings"
    config_ids = {entry["id"] for entry in rails}
    assert _enum_values(Rail) == config_ids


def test_downtime_windows_reference_known_rails(world_config: dict[str, Any]) -> None:
    """Every downtime window must name a rail that exists in the Rail enum.

    Downtime is what makes RETRY_ALTERNATE_RAIL worth learning. A window on an
    unknown rail would be unreachable ground truth.
    """
    known = _enum_values(Rail)
    for window in world_config["downtime_windows"]:
        assert window["rail"] in known, f"unknown rail in downtime window: {window['rail']}"


# ---------------------------------------------------------------------------
# The mirrored banding thresholds in app/core/banding.py
# ---------------------------------------------------------------------------


def test_amount_band_for_returns_only_enum_members() -> None:
    """amount_band_for returns a plain str; every value must be a valid AmountBand."""
    probes = [0, 1, 9_999, 10_000, 10_001, 100_000, 1_000_000, 5_000_000, 5_000_001, 10**12]
    for amount in probes:
        band = amount_band_for(amount)
        assert band in _enum_values(AmountBand), f"{amount} → unknown band {band!r}"


def test_banding_thresholds_agree_with_world_config(world_config: dict[str, Any]) -> None:
    """app/core/banding.py hard-codes thresholds; they must match the config.

    banding.py deliberately does not import app.sim, so its constants are a
    hand-mirrored copy. This test is the only thing standing between that copy
    and silent divergence — and a divergence here would mis-band amounts on
    the decision side while the world graded them in a different band.
    """
    bands = world_config["amount_bands"]
    ordered = list(bands.items())

    # Every band except the last must have an inclusive integer upper bound.
    for name, spec in ordered[:-1]:
        max_minor = spec["max_minor"]
        assert isinstance(max_minor, int), f"{name}.max_minor must be an int"
        assert amount_band_for(max_minor) == name, (
            f"{max_minor} paise should be the top of {name}, "
            f"but banding.py says {amount_band_for(max_minor)}"
        )

    # And one paise above each boundary must fall into the next band.
    for (_name, spec), (next_name, _) in zip(ordered[:-1], ordered[1:], strict=True):
        max_minor = spec["max_minor"]
        assert amount_band_for(max_minor + 1) == next_name, (
            f"{max_minor + 1} paise should be the bottom of {next_name}, "
            f"but banding.py says {amount_band_for(max_minor + 1)}"
        )

    # The final band is open-ended.
    assert ordered[-1][1]["max_minor"] is None, "the largest band must be unbounded"


def test_amount_band_for_rejects_negative_amounts() -> None:
    """Negative money is a programming error, not a band."""
    with pytest.raises(ValueError):
        amount_band_for(-1)
