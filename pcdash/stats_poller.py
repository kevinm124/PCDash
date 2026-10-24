"""Polls a DataProvider on a background thread so slow reads never stall the UI."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from .providers import DataProvider

log = logging.getLogger(__name__)


class _Worker(QObject):
    readings = Signal(dict)

    def __init__(self, provider: DataProvider, interval_ms: int) -> None:
        super().__init__()
        self._provider = provider
        self._interval_ms = interval_ms
        self._timer: QTimer | None = None

    @Slot()
    def start(self) -> None:
        # Created here so the timer lives in (and fires on) the worker thread.
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._poll)
        self._timer.start()
        self._poll()

    @Slot()
    def _poll(self) -> None:
        try:
            data = self._provider.poll()
        except Exception:
            log.exception("Provider %s failed to poll", self._provider.name)
            return
        self.readings.emit(data)


class StatsPoller(QObject):
    """Owns the worker thread. Connect to ``readings`` (delivered on the UI thread)."""

    readings = Signal(dict)

    def __init__(self, provider: DataProvider, interval_ms: int = 1000,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread = QThread(self)
        self._thread.setObjectName("StatsPoller")
        self._worker = _Worker(provider, interval_ms)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._thread.finished.connect(self._worker.deleteLater)
        self._worker.readings.connect(self.readings)

    def start(self) -> None:
        self._thread.start(QThread.Priority.LowPriority)

    def stop(self) -> None:
        self._thread.quit()
        self._thread.wait(2000)
