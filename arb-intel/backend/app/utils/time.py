"""Time utilities for the arbitrage scanner."""

from datetime import datetime, timedelta
import time


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.utcnow()


def timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


def seconds_until(target: datetime) -> int:
    """Calculate seconds until target datetime."""
    delta = target - utc_now()
    return max(0, int(delta.total_seconds()))


def estimate_expiry_seconds(
    last_update: datetime,
    typical_odds_lifetime_seconds: int = 60
) -> int:
    """
    Estimate seconds until opportunity likely expires.

    This is a heuristic based on typical odds movement patterns.
    """
    age_seconds = (utc_now() - last_update).total_seconds()
    remaining = typical_odds_lifetime_seconds - age_seconds
    return max(0, int(remaining))


class Timer:
    """Simple timer for measuring durations."""

    def __init__(self):
        self._start: float | None = None
        self._end: float | None = None

    def start(self) -> "Timer":
        """Start the timer."""
        self._start = time.perf_counter()
        self._end = None
        return self

    def stop(self) -> "Timer":
        """Stop the timer."""
        self._end = time.perf_counter()
        return self

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self._start is None:
            return 0.0
        end = self._end if self._end is not None else time.perf_counter()
        return (end - self._start) * 1000

    def __enter__(self) -> "Timer":
        return self.start()

    def __exit__(self, *args) -> None:
        self.stop()
