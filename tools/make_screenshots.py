"""Render README screenshots of every style into docs/screenshots/.

Uses fixed demo values, so the images look the same on any PC:

    .venv\\Scripts\\python.exe tools\\make_screenshots.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pcdash.gauges.styles import STYLES  # noqa: E402
from pcdash.overlay import OverlayWindow  # noqa: E402
from pcdash.providers.demo import SNAPSHOT, DemoProvider  # noqa: E402

OUT_DIR = ROOT / "docs" / "screenshots"
PAD = 24

# (file name, style, layout, main gauge)
SHOTS = [(f"{key}.png", key, "dashboard", "cpu") for key in STYLES] + [
    ("layout-grid.png", "futuristic", "grid", "cpu"),
    ("layout-single.png", "sporty", "single", "cpu"),
]


def _backdrop(size) -> QPixmap:
    """A desktop-wallpaper-like gradient so the transparent window shows."""
    pm = QPixmap(size.width() + 2 * PAD, size.height() + 2 * PAD)
    grad = QLinearGradient(QPointF(0, 0), QPointF(pm.width(), pm.height()))
    grad.setColorAt(0.0, QColor("#3d5a80"))
    grad.setColorAt(1.0, QColor("#98c1d9"))
    p = QPainter(pm)
    p.fillRect(QRectF(pm.rect()), grad)
    p.end()
    return pm


def main() -> int:
    app = QApplication(sys.argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    specs = DemoProvider().metrics()
    keys = [s.key for s in specs]
    for name, style, layout, main_key in SHOTS:
        window = OverlayWindow(specs, style)
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.set_layout(layout, keys, main_key)
        window.show()                       # off-screen; lays out the gauges
        app.processEvents()
        window.apply_readings(SNAPSHOT, snap=True)
        image = _backdrop(window.size())
        p = QPainter(image)
        p.drawPixmap(PAD, PAD, window.grab())
        p.end()
        image.save(str(OUT_DIR / name))
        print("wrote", OUT_DIR / name)
        window.allow_close()
        window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
