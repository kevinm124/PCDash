"""PC statistics provider (CPU for now; RAM, GPU and disks follow)."""

from __future__ import annotations

import psutil

from .base import DataProvider, MetricSpec, Reading


class PCStatsProvider(DataProvider):
    name = "PC stats"

    def __init__(self) -> None:
        # The first non-blocking cpu_percent() call always returns 0.0; prime
        # it so the first real poll reports usage since this moment.
        psutil.cpu_percent(interval=None)
        self._threads = psutil.cpu_count(logical=True) or 0

    def metrics(self) -> list[MetricSpec]:
        return [
            MetricSpec("cpu", "CPU", "%", redline=90, warn_above=90),
        ]

    def poll(self) -> dict[str, Reading]:
        cpu = psutil.cpu_percent(interval=None)
        return {"cpu": Reading(cpu, f"{self._threads} threads")}
