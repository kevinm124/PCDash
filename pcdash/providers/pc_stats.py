"""PC statistics provider: CPU, RAM, GPU/VRAM and free space per drive."""

from __future__ import annotations

import psutil

from .base import FUEL, DataProvider, MetricSpec, Reading
from .gpu import GpuBackend, detect_gpu

GIB = 1024 ** 3


def _gb(n: float) -> str:
    return f"{n / GIB:.1f}"


class PCStatsProvider(DataProvider):
    name = "PC stats"

    def __init__(self, gpu_backend: str = "auto") -> None:
        # The first non-blocking cpu_percent() call always returns 0.0; prime
        # it so the first real poll reports usage since this moment.
        psutil.cpu_percent(interval=None)
        self._threads = psutil.cpu_count(logical=True) or 0
        self._gpu: GpuBackend | None = detect_gpu(gpu_backend)
        # Fixed drives only (skips DVD drives and USB sticks).
        self._drives = [p.mountpoint for p in psutil.disk_partitions(all=False)
                        if p.fstype and "fixed" in p.opts]

    @staticmethod
    def _drive_key(mountpoint: str) -> str:
        return "disk:" + mountpoint.rstrip("\\:/")

    def metrics(self) -> list[MetricSpec]:
        specs = [
            MetricSpec("cpu", "CPU", red_zone=(90, 100), warn_above=90),
            MetricSpec("ram", "RAM", red_zone=(85, 100), warn_above=85),
        ]
        if self._gpu is not None:
            specs.append(MetricSpec("gpu", "GPU", red_zone=(90, 100), warn_above=95))
            if self._gpu.vram_total:
                specs.append(MetricSpec("vram", "VRAM", red_zone=(90, 100), warn_above=90))
        for mount in self._drives:
            key = self._drive_key(mount)
            specs.append(MetricSpec(key, key[5:] + ":", kind=FUEL, red_zone=(0, 10),
                                    warn_below=10, major_ticks=4, minor_ticks=2))
        return specs

    def poll(self) -> dict[str, Reading]:
        out: dict[str, Reading] = {}
        out["cpu"] = Reading(psutil.cpu_percent(interval=None), f"{self._threads} threads")

        mem = psutil.virtual_memory()
        out["ram"] = Reading(mem.percent, f"{_gb(mem.used)} / {_gb(mem.total)} GB")

        if self._gpu is not None:
            try:
                s = self._gpu.sample()
            except Exception:
                s = None
            if s is not None:
                out["gpu"] = Reading(s.usage, f"{s.temperature:.0f}°C"
                                     if s.temperature is not None else "")
                total = self._gpu.vram_total
                if total and s.vram_used is not None:
                    out["vram"] = Reading(100.0 * s.vram_used / total,
                                          f"{_gb(s.vram_used)} / {_gb(total)} GB")

        for mount in self._drives:
            try:
                du = psutil.disk_usage(mount)
            except OSError:
                continue
            free_pct = 100.0 * du.free / du.total if du.total else 0.0
            out[self._drive_key(mount)] = Reading(free_pct, f"{du.free / GIB:.0f} GB free")
        return out

    def close(self) -> None:
        if self._gpu is not None:
            self._gpu.close()
