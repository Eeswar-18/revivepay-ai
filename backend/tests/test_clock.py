"""
tests/test_clock.py — Behavioural tests for the VirtualClock.

Each test is named after and documents the property it protects.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import sleep

import pytest

from app.config import get_settings
from app.core.executor.clock import VirtualClock, clock


def test_virtual_clock_initialization_from_settings() -> None:
    """The global clock instance is initialized from settings."""
    settings = get_settings()
    assert clock.epoch_virtual == datetime.strptime(
        settings.VIRTUAL_EPOCH, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=UTC)
    assert clock.rate == settings.VIRTUAL_CLOCK_RATE


def test_virtual_clock_requires_start_before_now() -> None:
    """Calling now() before start() raises RuntimeError."""
    # Create a new clock instance to avoid interfering with the global singleton
    test_clock = VirtualClock(
        epoch_virtual=datetime(2024, 1, 1, tzinfo=UTC),
        rate=60.0,
    )
    with pytest.raises(RuntimeError, match="VirtualClock must be started"):
        test_clock.now()


def test_virtual_clock_start_sets_epoch_real() -> None:
    """start() records the current wall-clock time as epoch_real."""
    test_clock = VirtualClock(
        epoch_virtual=datetime(2024, 1, 1, tzinfo=UTC),
        rate=60.0,
    )
    # Freeze time conceptually: we'll check that epoch_real is set to near now
    before = datetime.now(UTC)
    test_clock.start()
    after = datetime.now(UTC)
    assert before <= test_clock.epoch_real <= after
    assert test_clock._started is True


def test_virtual_clock_now_returns_expected_virtual_time() -> None:
    """now() returns epoch_virtual + (real_elapsed * rate)."""
    # Use a known epoch and rate for predictability
    epoch_virtual = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    rate = 60.0  # 1 real second = 60 virtual seconds
    test_clock = VirtualClock(epoch_virtual=epoch_virtual, rate=rate)
    test_clock.start()

    # Wait a known amount of real time (approximately 1 second)
    sleep(1)  # Note: sleep is not precise but sufficient for this test
    virtual_now = test_clock.now()

    # Calculate expected virtual time: epoch_virtual + 1 real second * rate
    expected = epoch_virtual + timedelta(seconds=1 * rate)
    # Allow a small tolerance due to sleep imprecision
    assert abs((virtual_now - expected).total_seconds()) < 0.5


def test_virtual_clock_advance_shifts_epoch_virtual() -> None:
    """advance(hours) shifts epoch_virtual forward by the given hours."""
    test_clock = VirtualClock(
        epoch_virtual=datetime(2024, 1, 1, tzinfo=UTC),
        rate=60.0,
    )
    test_clock.start()
    original_epoch = test_clock.epoch_virtual
    test_clock.advance(5.5)
    expected = original_epoch + timedelta(hours=5.5)
    assert test_clock.epoch_virtual == expected


def test_virtual_clock_advance_rejects_negative_hours() -> None:
    """advance() with negative hours raises ValueError."""
    test_clock = VirtualClock(
        epoch_virtual=datetime(2024, 1, 1, tzinfo=UTC),
        rate=60.0,
    )
    test_clock.start()
    with pytest.raises(ValueError, match="Cannot advance virtual time by negative hours"):
        test_clock.advance(-1.0)


def test_virtual_clock_rate_must_be_positive() -> None:
    """VirtualClock construction with non-positive rate raises ValueError."""
    with pytest.raises(ValueError, match="Virtual clock rate must be positive"):
        VirtualClock(epoch_virtual=datetime(2024, 1, 1, tzinfo=UTC), rate=0.0)
    with pytest.raises(ValueError, match="Virtual clock rate must be positive"):
        VirtualClock(epoch_virtual=datetime(2024, 1, 1, tzinfo=UTC), rate=-1.0)


def test_virtual_clock_epoch_virtual_is_timezone_aware() -> None:
    """epoch_virtual is stored as timezone-aware UTC even if given naive."""
    naive = datetime(2024, 1, 1, 12, 0, 0)  # no timezone
    test_clock = VirtualClock(epoch_virtual=naive, rate=60.0)
    # __post_init__ should have attached UTC timezone
    assert test_clock.epoch_virtual.tzinfo == UTC
    assert test_clock.epoch_virtual == naive.replace(tzinfo=UTC)
