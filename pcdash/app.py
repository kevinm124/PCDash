"""Application setup: create the provider, the style and the overlay window."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from .gauges.styles import DEFAULT_STYLE, create_style
from .overlay import OverlayWindow
from .providers.pc_stats import PCStatsProvider


def main(argv: list[str] | None = None) -> int:
    # Use exact Windows scaling (e.g. 125%) instead of rounding, for crisp gauges.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("PCDash")

    provider = PCStatsProvider()
    window = OverlayWindow(provider, create_style(DEFAULT_STYLE))
    window.show()
    try:
        return app.exec()
    finally:
        provider.close()
