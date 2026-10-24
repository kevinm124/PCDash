"""Fake, smoothly changing stats: for trying styles and warning lamps
(``python main.py --demo``) and for making consistent screenshots."""

from __future__ import annotations

import math
import time

from .base import DataProvider, MetricSpec, Reading
from .pc_stats import CPU_SPEC, GPU_SPEC, RAM_SPEC, VRAM_SPEC, drive_spec

# A fixed, good-looking moment for screenshots (CPU and C: in the red).
SNAPSHOT: dict[str, Reading] = {
    "cpu": Reading(93, "12 threads"),
    "ram": Reading(64, "10.2 / 15.9 GB"),
    "gpu": Reading(71, "66°C"),
    "vram": Reading(48, "3.8 / 8.0 GB"),
    "disk:C": Reading(8, "37 GB free"),
    "disk:D": Reading(62, "580 GB free"),
}


def _wave(t: float, center: float, amplitude: float, period: float,
          phase: float = 0.0) -> float:
    value = center + amplitude * math.sin(2 * math.pi * t / period + phase)
    return max(0.0, min(100.0, value))


class DemoProvider(DataProvider):
    name = "Demo"

    def __init__(self) -> None:
        self._start = time.monotonic()

    def metrics(self) -> list[MetricSpec]:
        return [CPU_SPEC, RAM_SPEC, GPU_SPEC, VRAM_SPEC, drive_spec("C"), drive_spec("D")]

    def poll(self) -> dict[str, Reading]:
        t = time.monotonic() - self._start
        cpu = _wave(t, 55, 42, 14) + 4 * math.sin(t * 1.9)
        ram = _wave(t, 72, 18, 23, 1.0)
        gpu = _wave(t, 50, 49, 11, 2.0)
        vram = _wave(t, 45, 35, 31, 0.5)
        c_free = _wave(t, 18, 14, 37, 3.0)
        return {
            "cpu": Reading(max(0.0, min(100.0, cpu)), "12 threads"),
            "ram": Reading(ram, f"{ram * 0.159:.1f} / 15.9 GB"),
            "gpu": Reading(gpu, f"{40 + gpu * 0.4:.0f}°C"),
            "vram": Reading(vram, f"{vram * 0.08:.1f} / 8.0 GB"),
            "disk:C": Reading(c_free, f"{c_free * 4.65:.0f} GB free"),
            "disk:D": Reading(62, "580 GB free"),
        }
