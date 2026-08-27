"""
core/executor/clock.py — Virtual clock for deterministic time simulation.

All time-aware code in the decision pipeline and executor must read from
this virtual clock rather than `datetime.now()` or `timezone.now()` to ensure
reproducible simulations and testable time-dependent behavior.

The virtual clock maps real time (wall-clock) to virtual simulation time via:
    virtual_time = epoch_virtual + (real_time - epoch_real) * rate

Where:
- epoch_real: wall-clock time when the simulation started (set at initialization)
- epoch_virtual: virtual time at simulation start (configurable via settings)
- rate: virtual seconds per real second (default: 60.0, meaning 1 real second = 60 virtual seconds)

The clock provides:
- now() -> datetime: current virtual time (timezone-aware UTC)
- advance(hours) -> None: teleport virtual time forward by given hours (test helper)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.config.settings import get_settings


@dataclass
class VirtualClock:
    """Virtual clock for deterministic time simulation.

    Attributes
    ----------
    epoch_real: datetime
        Wall-clock time when the simulation started (set at initialization).
    epoch_virtual: datetime
        Virtual time at simulation start (configurable via settings).
    rate: float
        Virtual seconds per real second (default: 60.0).
    _started: bool
        Internal flag tracking whether the clock has been started.
    """

    epoch_real: datetime = field(init=False)
    epoch_virtual: datetime
    rate: float
    _started: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.rate <= 0:
            raise ValueError(f"Virtual clock rate must be positive, got {self.rate}")
        # Ensure datetimes are timezone-aware (UTC)
        if self.epoch_virtual.tzinfo is None:
            object.__setattr__(self, "epoch_virtual", self.epoch_virtual.replace(tzinfo=UTC))

    def start(self) -> None:
        """Start the clock, recording the current wall-clock time as epoch_real.

        This method must be called exactly once before using ``now()``.
        Calling it multiple times will reset the epoch, which may cause
        unexpected behavior in long-running simulations.
        """
        if self._started:
            # Allow restarting for test scenarios, but warn via logic if needed
            pass
        self.epoch_real = datetime.now(UTC)
        self._started = True

    def now(self) -> datetime:
        """Return the current virtual time as a timezone-aware UTC datetime.

        Returns
        -------
        datetime
            Current virtual time in UTC.

        Raises
        ------
        RuntimeError
            If the clock has not been started via ``start()``.
        """
        if not self._started:
            raise RuntimeError(
                "VirtualClock must be started before calling now(). "
                "Call clock.start() at the beginning of the simulation."
            )

        # Calculate elapsed real time since epoch_real
        real_now = datetime.now(UTC)
        elapsed_real = real_now - self.epoch_real

        # Convert to virtual time: epoch_virtual + (elapsed_real * rate)
        elapsed_virtual = timedelta(seconds=elapsed_real.total_seconds() * self.rate)
        return self.epoch_virtual + elapsed_virtual

    def advance(self, hours: float) -> None:
        """Teleport virtual time forward by the given number of hours.

        This is a test helper that allows instant time travel in virtual time
        without waiting for real time to pass. It does not affect the epoch_real
        or rate; it simply shifts the epoch_virtual forward.

        Parameters
        ----------
        hours: float
            Number of hours to advance virtual time (can be fractional).

        Raises
        ------
        ValueError
            If hours is negative.
        """
        if hours < 0:
            raise ValueError(f"Cannot advance virtual time by negative hours: {hours}")

        # Shift the virtual epoch forward by the given hours
        advance_delta = timedelta(hours=hours)
        object.__setattr__(self, "epoch_virtual", self.epoch_virtual + advance_delta)


# Global singleton instance for application-wide use.
# The clock must be started by the application entry point (main.py) before use.
_settings = get_settings()
# Parse the VIRTUAL_EPOCH string (expected format: "2024-01-01T00:00:00Z")
_epoch_virtual = datetime.strptime(_settings.VIRTUAL_EPOCH, "%Y-%m-%dT%H:%M:%SZ").replace(
    tzinfo=UTC
)

clock = VirtualClock(
    epoch_virtual=_epoch_virtual,
    rate=_settings.VIRTUAL_CLOCK_RATE,
)
