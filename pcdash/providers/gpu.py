"""GPU usage backends.

* ``NvmlGpu``  - NVIDIA cards via NVML (nvidia-ml-py). Accurate and cheap.
* ``PdhGpu``   - any GPU (AMD, Intel, NVIDIA) via the Windows "GPU Engine" and
  "GPU Adapter Memory" performance counters, the same data Task Manager shows.

``detect_gpu()`` returns the first backend that works, or ``None``.
"""

from __future__ import annotations

import ctypes
import logging
import re
import sys
import winreg
from abc import ABC, abstractmethod
from collections import defaultdict
from ctypes import wintypes
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpuSample:
    usage: float                  # percent
    vram_used: int | None         # bytes
    temperature: float | None     # degrees C


class GpuBackend(ABC):
    name: str = "GPU"             # adapter name, e.g. "NVIDIA GeForce GTX 1070 Ti"
    vram_total: int | None = None # bytes, None if unknown

    @abstractmethod
    def sample(self) -> GpuSample: ...

    def close(self) -> None: ...


# --- NVIDIA / NVML ---------------------------------------------------------

class NvmlGpu(GpuBackend):
    def __init__(self, index: int = 0) -> None:
        import pynvml  # provided by the nvidia-ml-py package

        self._nvml = pynvml
        pynvml.nvmlInit()
        try:
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            name = pynvml.nvmlDeviceGetName(self._handle)
            self.name = name.decode() if isinstance(name, bytes) else name
            self.vram_total = int(pynvml.nvmlDeviceGetMemoryInfo(self._handle).total)
        except Exception:
            pynvml.nvmlShutdown()
            raise

    def sample(self) -> GpuSample:
        nv = self._nvml
        usage = float(nv.nvmlDeviceGetUtilizationRates(self._handle).gpu)
        used = int(nv.nvmlDeviceGetMemoryInfo(self._handle).used)
        try:
            temp = float(nv.nvmlDeviceGetTemperature(self._handle, nv.NVML_TEMPERATURE_GPU))
        except nv.NVMLError:
            temp = None
        return GpuSample(usage, used, temp)

    def close(self) -> None:
        try:
            self._nvml.nvmlShutdown()
        except Exception:
            pass


# --- Windows performance counters (PDH) ------------------------------------

_PDH_FMT_DOUBLE = 0x00000200
_PDH_FMT_LARGE = 0x00000400
_PDH_MORE_DATA = 0x800007D2
_PDH_CSTATUS_VALID = (0x0, 0x1)   # VALID_DATA, NEW_DATA


class _FmtValue(ctypes.Structure):
    # PDH_FMT_COUNTERVALUE: DWORD status followed by an 8-byte-aligned union.
    _fields_ = [("CStatus", wintypes.DWORD), ("value", ctypes.c_double)]


class _FmtValueLarge(ctypes.Structure):
    _fields_ = [("CStatus", wintypes.DWORD), ("value", ctypes.c_longlong)]


def _item_type(value_type: type[ctypes.Structure]) -> type[ctypes.Structure]:
    class Item(ctypes.Structure):
        _fields_ = [("szName", ctypes.c_wchar_p), ("FmtValue", value_type)]
    return Item


_ItemDouble = _item_type(_FmtValue)
_ItemLarge = _item_type(_FmtValueLarge)

# "pid_1234_luid_0x00000000_0x0000C1E4_phys_0_eng_3_engtype_3D"
_ENGINE_RE = re.compile(r"luid_(0x[0-9a-fA-F]+_0x[0-9a-fA-F]+)_phys_\d+_eng_\d+_engtype_(.*)$")
_ADAPTER_RE = re.compile(r"luid_(0x[0-9a-fA-F]+_0x[0-9a-fA-F]+)_phys_\d+$")


class PdhGpu(GpuBackend):
    """GPU usage from Windows performance counters (works for any vendor)."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("PDH is only available on Windows")
        pdh = ctypes.WinDLL("pdh")
        for fn in ("PdhOpenQueryW", "PdhAddEnglishCounterW", "PdhCollectQueryData",
                   "PdhGetFormattedCounterArrayW", "PdhCloseQuery"):
            getattr(pdh, fn).restype = ctypes.c_uint32
        self._pdh = pdh

        self._query = wintypes.HANDLE()
        self._check(pdh.PdhOpenQueryW(None, None, ctypes.byref(self._query)))
        self._engine = self._add(r"\GPU Engine(*)\Utilization Percentage")
        self._memory = self._add(r"\GPU Adapter Memory(*)\Dedicated Usage")
        self._check(pdh.PdhCollectQueryData(self._query))  # baseline for rates

        self.name, self.vram_total = _largest_display_adapter()

    def _check(self, status: int) -> None:
        if status != 0:
            raise OSError(f"PDH call failed: 0x{status:08X}")

    def _add(self, path: str) -> wintypes.HANDLE:
        counter = wintypes.HANDLE()
        self._check(self._pdh.PdhAddEnglishCounterW(self._query, path, None,
                                                    ctypes.byref(counter)))
        return counter

    def _values(self, counter: wintypes.HANDLE, large: bool) -> dict[str, float]:
        fmt, item = (_PDH_FMT_LARGE, _ItemLarge) if large else (_PDH_FMT_DOUBLE, _ItemDouble)
        size, count = wintypes.DWORD(0), wintypes.DWORD(0)
        status = self._pdh.PdhGetFormattedCounterArrayW(counter, fmt, ctypes.byref(size),
                                                        ctypes.byref(count), None)
        if status != _PDH_MORE_DATA:
            return {}
        buf = (ctypes.c_byte * size.value)()
        status = self._pdh.PdhGetFormattedCounterArrayW(counter, fmt, ctypes.byref(size),
                                                        ctypes.byref(count), buf)
        if status != 0:
            return {}
        items = ctypes.cast(buf, ctypes.POINTER(item * count.value)).contents
        return {it.szName: float(it.FmtValue.value) for it in items
                if it.FmtValue.CStatus in _PDH_CSTATUS_VALID}

    def sample(self) -> GpuSample:
        self._pdh.PdhCollectQueryData(self._query)

        # Dedicated memory per adapter; the busiest adapter is the real GPU
        # (skips the "Microsoft Basic Display Adapter").
        memory: dict[str, float] = {}
        for name, value in self._values(self._memory, large=True).items():
            if m := _ADAPTER_RE.search(name):
                memory[m.group(1)] = memory.get(m.group(1), 0.0) + value
        luid = max(memory, key=memory.get) if memory else None

        # Like Task Manager: sum each engine type over all processes, then
        # report the busiest engine type (3D, Copy, VideoDecode, ...).
        per_engine: dict[tuple[str, str], float] = defaultdict(float)
        for name, value in self._values(self._engine, large=False).items():
            if (m := _ENGINE_RE.search(name)) and (luid is None or m.group(1) == luid):
                per_engine[(m.group(1), m.group(2))] += value
        usage = min(100.0, max(per_engine.values(), default=0.0))

        used = int(memory[luid]) if luid else None
        return GpuSample(usage, used, None)

    def close(self) -> None:
        if self._query:
            self._pdh.PdhCloseQuery(self._query)
            self._query = wintypes.HANDLE()


def _largest_display_adapter() -> tuple[str, int | None]:
    """Name and VRAM size of the display adapter with the most memory.

    PDH reports VRAM *usage* but not the total, so read it from the display
    driver's registry entries (``HardwareInformation.qwMemorySize``).
    """
    best_name, best_size = "GPU", None
    class_key = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, class_key)
    except OSError:
        return best_name, best_size
    with root:
        index = 0
        while True:
            try:
                sub = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1
            try:
                with winreg.OpenKey(root, sub) as key:
                    size, _ = winreg.QueryValueEx(key, "HardwareInformation.qwMemorySize")
                    name, _ = winreg.QueryValueEx(key, "DriverDesc")
            except OSError:
                continue
            size = int.from_bytes(size, "little") if isinstance(size, bytes) else int(size)
            if best_size is None or size > best_size:
                best_name, best_size = str(name), size
    return best_name, best_size


def detect_gpu(prefer: str = "auto") -> GpuBackend | None:
    """Return a working GPU backend. ``prefer`` may be "auto", "nvml" or "pdh"."""
    order = {"nvml": [NvmlGpu], "pdh": [PdhGpu]}.get(prefer, [NvmlGpu, PdhGpu])
    for backend in order:
        try:
            gpu = backend()
            log.info("GPU backend: %s (%s)", backend.__name__, gpu.name)
            return gpu
        except Exception as exc:  # driver missing, no NVIDIA card, counters disabled...
            log.info("GPU backend %s unavailable: %s", backend.__name__, exc)
    return None
