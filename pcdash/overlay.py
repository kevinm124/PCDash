"""The overlay window: frameless, transparent and always on top."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QGridLayout, QHBoxLayout, QMenu, QWidget

from .gauges import GaugeWidget
from .gauges.styles import GaugeStyle
from .providers import DataProvider, Reading
from .providers.base import FUEL
from .stats_poller import StatsPoller

SMALL = 150     # default size of a small gauge, in logical pixels
SPACING = 6


class OverlayWindow(QWidget):
    POLL_MS = 1000

    def __init__(self, provider: DataProvider, style: GaugeStyle) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,             # no taskbar button
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("PCDash")

        self._gauges: dict[str, GaugeWidget] = {}
        self._build_dashboard(provider, style)

        self._poller = StatsPoller(provider, self.POLL_MS, self)
        self._poller.readings.connect(self._apply_readings)
        self._poller.start()

    def _build_dashboard(self, provider: DataProvider, style: GaugeStyle) -> None:
        """Big main gauge on the left; dials on the top row and fuel gauges
        (drives) on the bottom row of a grid on the right."""
        specs = provider.metrics()
        main, rest = specs[0], specs[1:]
        dials = [s for s in rest if s.kind != FUEL]
        fuels = [s for s in rest if s.kind == FUEL]
        cols = max(len(dials), len(fuels), 1)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING)
        root.addWidget(self._make_gauge(main, style), 2)

        grid = QGridLayout()
        grid.setSpacing(SPACING)
        for row, group in enumerate((dials, fuels)):
            for col, spec in enumerate(group):
                grid.addWidget(self._make_gauge(spec, style), row, col)
        for col in range(cols):
            grid.setColumnStretch(col, 1)
        root.addLayout(grid, cols)

        rows = 2 if dials and fuels else 1
        height = rows * SMALL + (rows - 1) * SPACING
        self.resize(height + SPACING + cols * SMALL + (cols - 1) * SPACING, height)

    def _make_gauge(self, spec, style: GaugeStyle) -> GaugeWidget:
        gauge = GaugeWidget(spec, style, self)
        self._gauges[spec.key] = gauge
        return gauge

    def _apply_readings(self, readings: dict[str, Reading]) -> None:
        for key, reading in readings.items():
            gauge = self._gauges.get(key)
            if gauge is not None:
                gauge.set_reading(reading)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._poller.stop()
        super().closeEvent(event)

    # --- interaction -------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Native move: smooth and snaps to screen edges like a normal window.
            self.windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        menu.addAction("Quit", QApplication.quit)
        menu.exec(event.globalPos())
