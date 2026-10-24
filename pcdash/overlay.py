"""The overlay window: frameless, transparent and always on top.

The window is a view only: it lays out gauges and reports user gestures via
signals. ``Controller`` decides what to do with them and saves settings.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import (QCloseEvent, QContextMenuEvent, QMouseEvent,
                           QMoveEvent, QShowEvent, QWheelEvent)
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from . import win32
from .gauges import GaugeWidget
from .gauges.styles import create_style
from .providers import MetricSpec, Reading
from .providers.base import FUEL

SMALL = 150     # small gauge in the dashboard layout, in logical pixels
CELL = 170      # gauge size in the row and grid layouts
BIG = 300       # single-gauge layout
SPACING = 6


class OverlayWindow(QWidget):
    moved = Signal(QPoint)            # new top-left position
    menu_requested = Signal(QPoint)   # global position of a right-click
    scale_step = Signal(int)          # Ctrl + mouse wheel (+1 / -1 per notch)
    opacity_step = Signal(int)        # Shift + mouse wheel
    close_requested = Signal()        # Alt+F4: hide rather than quit

    def __init__(self, specs: list[MetricSpec], style_key: str) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,             # no taskbar button
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("PCDash")

        self._specs = specs
        self._style = create_style(style_key)
        self._gauges: dict[str, GaugeWidget] = {}
        self._last: dict[str, Reading] = {}
        self._base = QSize(BIG, BIG)
        self._scale = 1.0
        self._click_through = False
        self._closing = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._body: QWidget | None = None

    # --- layout ------------------------------------------------------------

    def set_layout(self, layout: str, visible: list[str], main_key: str) -> None:
        """(Re)build the gauges. ``visible`` is the ordered list of keys to show."""
        specs = [s for s in self._specs if s.key in visible] or self._specs[:1]
        main = next((s for s in specs if s.key == main_key), specs[0])

        if self._body is not None:
            self._body.hide()
            self._body.deleteLater()
        self._gauges.clear()
        body = QWidget(self)
        self.layout().addWidget(body)
        self._body = body

        if layout == "single":
            self._base = self._build_single(body, main)
        elif layout == "row":
            self._base = self._build_grid(body, specs, cols=len(specs))
        elif layout == "grid":
            self._base = self._build_grid(body, specs, cols=math.ceil(math.sqrt(len(specs))))
        else:
            self._base = self._build_dashboard(body, main, [s for s in specs if s is not main])

        for key, reading in self._last.items():
            if key in self._gauges:
                self._gauges[key].set_reading(reading, snap=True)
        self._apply_size()

    def _gauge(self, spec: MetricSpec, parent: QWidget) -> GaugeWidget:
        gauge = GaugeWidget(spec, self._style, parent)
        self._gauges[spec.key] = gauge
        return gauge

    def _build_single(self, body: QWidget, spec: MetricSpec) -> QSize:
        box = QHBoxLayout(body)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self._gauge(spec, body))
        return QSize(BIG, BIG)

    def _build_grid(self, body: QWidget, specs: list[MetricSpec], cols: int) -> QSize:
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(SPACING)
        for i, spec in enumerate(specs):
            grid.addWidget(self._gauge(spec, body), i // cols, i % cols)
        rows = math.ceil(len(specs) / cols)
        return QSize(cols * CELL + (cols - 1) * SPACING, rows * CELL + (rows - 1) * SPACING)

    def _build_dashboard(self, body: QWidget, main: MetricSpec,
                         rest: list[MetricSpec]) -> QSize:
        """Big main gauge on the left; dials on the top row and fuel gauges
        (drives) on the bottom row of a grid on the right."""
        root = QHBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING)
        root.addWidget(self._gauge(main, body), 2)
        if not rest:
            return QSize(BIG, BIG)

        dials = [s for s in rest if s.kind != FUEL]
        fuels = [s for s in rest if s.kind == FUEL]
        cols = max(len(dials), len(fuels))
        grid = QGridLayout()
        grid.setSpacing(SPACING)
        for row, group in enumerate(g for g in (dials, fuels) if g):
            for col, spec in enumerate(group):
                grid.addWidget(self._gauge(spec, body), row, col)
        for col in range(cols):
            grid.setColumnStretch(col, 1)
        root.addLayout(grid, cols)

        rows = 2 if dials and fuels else 1
        height = rows * SMALL + (rows - 1) * SPACING
        return QSize(height + SPACING + cols * SMALL + (cols - 1) * SPACING, height)

    # --- appearance --------------------------------------------------------

    def set_style(self, key: str) -> None:
        """Switch every gauge to another style at runtime."""
        if key == self._style.key:
            return
        self._style = create_style(key)
        for gauge in self._gauges.values():
            gauge.set_style(self._style)

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self._apply_size()

    def _apply_size(self) -> None:
        self.setFixedSize(round(self._base.width() * self._scale),
                          round(self._base.height() * self._scale))

    def set_click_through(self, enabled: bool) -> None:
        self._click_through = enabled
        win32.set_click_through(int(self.winId()), enabled)

    # --- data --------------------------------------------------------------

    def apply_readings(self, readings: dict[str, Reading], snap: bool = False) -> None:
        self._last.update(readings)
        if not self.isVisible():
            return      # no animation work while hidden; showEvent catches up
        for key, reading in readings.items():
            gauge = self._gauges.get(key)
            if gauge is not None:
                gauge.set_reading(reading, snap)

    # --- events ------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        # Re-apply in case the native window style was reset.
        win32.set_click_through(int(self.winId()), self._click_through)
        for key, reading in self._last.items():
            if key in self._gauges:
                self._gauges[key].set_reading(reading, snap=True)

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self.moved.emit(self.pos())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Native move: smooth and snaps to screen edges like a normal window.
            self.windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y() or event.angleDelta().x()
        step = 1 if delta > 0 else -1 if delta < 0 else 0
        mods = event.modifiers()
        if step and mods & Qt.KeyboardModifier.ControlModifier:
            self.scale_step.emit(step)
        elif step and mods & Qt.KeyboardModifier.ShiftModifier:
            self.opacity_step.emit(step)
        else:
            super().wheelEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.menu_requested.emit(event.globalPos())

    def allow_close(self) -> None:
        """Called when the app is really quitting."""
        self._closing = True

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            super().closeEvent(event)
            return
        # Alt+F4 on the overlay hides it instead of quitting (tray stays).
        event.ignore()
        self.close_requested.emit()
