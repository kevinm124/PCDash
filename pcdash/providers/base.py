"""Data provider interface.

A provider knows *what* to measure and *how* to read it, but nothing about how
it is drawn. The overlay asks a provider which metrics it offers (``metrics``)
and then calls ``poll`` on a timer to get fresh readings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

DIAL = "dial"   # round tachometer-style gauge
FUEL = "fuel"   # fuel-gauge style: short arc from E to F


@dataclass(frozen=True)
class MetricSpec:
    """Static description of one gauge's data: its range, units and limits."""

    key: str                          # stable id, e.g. "cpu", "disk:C"
    label: str                        # short text drawn on the gauge face
    unit: str = "%"
    minimum: float = 0.0
    maximum: float = 100.0
    kind: str = DIAL                  # DIAL or FUEL; styles draw each differently
    red_zone: tuple[float, float] | None = None   # value range painted red
    warn_above: float | None = None   # warning lamp on when value >= this
    warn_below: float | None = None   # warning lamp on when value <= this
    major_ticks: int = 10             # number of major divisions
    minor_ticks: int = 5              # minor divisions per major division

    def clamp(self, value: float) -> float:
        return max(self.minimum, min(self.maximum, value))

    def fraction(self, value: float) -> float:
        span = self.maximum - self.minimum
        return 0.0 if span <= 0 else (self.clamp(value) - self.minimum) / span

    def in_red_zone(self, value: float) -> bool:
        if self.red_zone is None:
            return False
        low, high = self.red_zone
        return low - 1e-9 <= value <= high + 1e-9

    def is_warning(self, value: float) -> bool:
        if self.warn_above is not None and value >= self.warn_above:
            return True
        if self.warn_below is not None and value <= self.warn_below:
            return True
        return False


@dataclass(frozen=True)
class Reading:
    """One sampled value for a metric, plus optional secondary text."""

    value: float
    detail: str = ""                  # e.g. "7.9 / 16.0 GB"


class DataProvider(ABC):
    """Source of live values for the gauges.

    ``poll`` is called from a background thread, so it may take a few
    milliseconds without stuttering the animation.
    """

    name: str = "provider"

    @abstractmethod
    def metrics(self) -> list[MetricSpec]:
        """All metrics this provider can report, in default display order."""

    @abstractmethod
    def poll(self) -> dict[str, Reading]:
        """Return the latest reading for each metric key."""

    def close(self) -> None:
        """Release any resources (driver handles, counter queries)."""
