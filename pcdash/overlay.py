"""The overlay window: frameless, transparent and always on top."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMenu, QWidget

from .gauges import GaugeWidget
from .gauges.styles import GaugeStyle
from .providers import DataProvider


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
        self._provider = provider

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._gauges: dict[str, GaugeWidget] = {}
        for spec in provider.metrics():
            gauge = GaugeWidget(spec, style, self)
            layout.addWidget(gauge)
            self._gauges[spec.key] = gauge
        self.resize(300, 300)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self.POLL_MS)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()
        self._poll()

    def _poll(self) -> None:
        for key, reading in self._provider.poll().items():
            gauge = self._gauges.get(key)
            if gauge is not None:
                gauge.set_reading(reading)

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
