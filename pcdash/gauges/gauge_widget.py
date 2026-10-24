"""A single gauge: smooth needle animation on top of a cached static face."""

from __future__ import annotations

import math
import time

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QPainter, QPaintEvent, QPixmap, QResizeEvent
from PySide6.QtWidgets import QWidget

from ..providers.base import MetricSpec, Reading
from .styles.base import GaugeState, GaugeStyle


class GaugeWidget(QWidget):
    FRAME_MS = 33          # ~30 fps while the needle is moving (see set_fps)
    SMOOTHING = 6.0        # 1/s; higher = snappier needle

    @classmethod
    def set_fps(cls, fps: int) -> None:
        """Animation frame rate for gauges created afterwards."""
        cls.FRAME_MS = max(1, round(1000 / fps))

    def __init__(self, spec: MetricSpec, style: GaugeStyle,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spec = spec
        self._style = style
        self._target = spec.minimum
        self._shown = spec.minimum
        self._detail = ""
        self._cache: QPixmap | None = None
        self._last_tick = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._tick)

        self.setMinimumSize(40, 40)

    # --- public API --------------------------------------------------------

    @property
    def spec(self) -> MetricSpec:
        return self._spec

    def set_style(self, style: GaugeStyle) -> None:
        self._style = style
        self._cache = None
        self.update()

    def set_reading(self, reading: Reading, snap: bool = False) -> None:
        """Move toward ``reading``; ``snap`` jumps there without animating."""
        self._target = self._spec.clamp(reading.value)
        if snap:
            self._shown = self._target
            self._detail = reading.detail
            self.update()
            return
        if reading.detail != self._detail:
            self._detail = reading.detail
            self.update()
        if not self._timer.isActive() and abs(self._target - self._shown) > self._epsilon():
            self._last_tick = time.perf_counter()
            self._timer.start()

    def sizeHint(self) -> QSize:
        return QSize(260, 260)

    # --- animation ---------------------------------------------------------

    def _epsilon(self) -> float:
        return (self._spec.maximum - self._spec.minimum) * 0.001

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = min(now - self._last_tick, 0.1)
        self._last_tick = now
        diff = self._target - self._shown
        if abs(diff) <= self._epsilon():
            self._shown = self._target
            self._timer.stop()
        else:
            # Exponential ease-out: fast at first, settling gently.
            self._shown += diff * (1.0 - math.exp(-self.SMOOTHING * dt))
        self.update()

    # --- painting ----------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent) -> None:
        self._cache = None
        super().resizeEvent(event)

    def _background(self) -> QPixmap:
        dpr = self.devicePixelRatioF()
        if self._cache is None or self._cache.devicePixelRatio() != dpr:
            pm = QPixmap(max(1, round(self.width() * dpr)), max(1, round(self.height() * dpr)))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.GlobalColor.transparent)
            qp = QPainter(pm)
            qp.setRenderHints(QPainter.RenderHint.Antialiasing
                              | QPainter.RenderHint.TextAntialiasing)
            self._style.paint_background(qp, QRectF(0, 0, self.width(), self.height()),
                                         self._spec)
            qp.end()
            self._cache = pm
        return self._cache

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing
                         | QPainter.RenderHint.TextAntialiasing)
        p.drawPixmap(0, 0, self._background())
        state = GaugeState(self._shown, self._detail, self._spec.is_warning(self._target))
        self._style.paint_foreground(p, QRectF(self.rect()), self._spec, state)
        p.end()
