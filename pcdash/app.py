"""Application setup: load settings, create the provider and the controller."""

from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .config import APP_DIR, Settings
from .controller import Controller
from .gauges import GaugeWidget
from .providers import DataProvider

LOG_PATH = APP_DIR / "pcdash.log"
log = logging.getLogger("pcdash")


def _setup_logging() -> None:
    """Log to %APPDATA%\\PCDash\\pcdash.log, and to the console if there is one
    (there is none under pythonw.exe)."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(LOG_PATH, maxBytes=512_000, backupCount=1, encoding="utf-8")
    ]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    def excepthook(exc_type, exc, tb):
        log.critical("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = excepthook


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pcdash", description="PC stats as car gauges.")
    parser.add_argument("--demo", action="store_true",
                        help="show fake, moving data instead of real PC stats")
    parser.add_argument("--version", action="version", version=f"PCDash {__version__}")
    args, _qt_args = parser.parse_known_args(argv[1:])
    return args


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv)
    args = _parse_args(argv)
    _setup_logging()
    log.info("PCDash %s starting%s", __version__, " (demo mode)" if args.demo else "")

    # Use exact Windows scaling (e.g. 125%) instead of rounding, for crisp gauges.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv)
    app.setApplicationName("PCDash")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)      # lives in the tray

    # Only one instance: a second one would fight over the hotkeys.
    lock = QLockFile(str(APP_DIR / "pcdash.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, "PCDash",
                                "PCDash is already running - look for its tray icon.")
        return 0

    settings = Settings.load()
    GaugeWidget.set_fps(settings.animation_fps)
    provider: DataProvider
    if args.demo:
        from .providers.demo import DemoProvider
        provider = DemoProvider()
    else:
        from .providers.pc_stats import PCStatsProvider
        provider = PCStatsProvider(settings.gpu_backend)

    controller = Controller(settings, provider)
    try:
        return app.exec()
    finally:
        controller.shutdown()
        lock.unlock()
        log.info("PCDash stopped")
