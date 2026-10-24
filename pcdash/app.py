"""Application setup: load settings, create the provider and the controller."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from .config import APP_DIR, Settings
from .controller import Controller
from .gauges import GaugeWidget
from .providers.pc_stats import PCStatsProvider


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # Use exact Windows scaling (e.g. 125%) instead of rounding, for crisp gauges.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("PCDash")
    app.setQuitOnLastWindowClosed(False)      # lives in the tray

    # Only one instance: a second one would fight over the hotkeys.
    APP_DIR.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(APP_DIR / "pcdash.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, "PCDash",
                                "PCDash is already running - look for its tray icon.")
        return 0

    settings = Settings.load()
    GaugeWidget.set_fps(settings.animation_fps)
    provider = PCStatsProvider(settings.gpu_backend)
    controller = Controller(settings, provider)
    try:
        return app.exec()
    finally:
        controller.shutdown()
        lock.unlock()
