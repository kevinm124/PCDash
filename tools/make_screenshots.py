"""Render the README pictures into docs/screenshots/.

Uses demo values, so the images look the same on any PC:

    .venv\\Scripts\\python.exe tools\\make_screenshots.py

Animated GIFs need Pillow (``pip install -r requirements-dev.txt``); without
it only the PNGs are made.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Show a generic path in the Settings window screenshot, not this PC's.
os.environ["PCDASH_CONFIG"] = r"%APPDATA%\PCDash\config.json"

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pcdash.config import Settings  # noqa: E402
from pcdash.gauges.styles import STYLES  # noqa: E402
from pcdash.overlay import OverlayWindow  # noqa: E402
from pcdash.providers.demo import SNAPSHOT, DemoProvider  # noqa: E402
from pcdash.settings_dialog import SettingsDialog  # noqa: E402

OUT_DIR = ROOT / "docs" / "screenshots"
PAD = 24

# (file name, style, layout, main gauge)
SHOTS = [(f"{key}.png", key, "dashboard", "cpu") for key in STYLES] + [
    ("layout-grid.png", "futuristic", "grid", "cpu"),
    ("layout-single.png", "sporty", "single", "cpu"),
    ("layout-row.png", "retro", "row", "cpu"),
]

# (file name, style, scale, palette size) for animated demos. Sporty's
# gradients bloat the file at 256 colours; Futuristic needs them for its neon.
GIFS = [("demo-sporty.gif", "sporty", 0.75, 128),
        ("demo-futuristic.gif", "futuristic", 0.75, 256)]
GIF_FRAMES = 60
GIF_FRAME_MS = 66            # ~15 fps
GIF_DEMO_SECONDS = 15.0      # demo time covered by one loop (sped up ~3.7x)


def _backdrop(width: int, height: int) -> QPixmap:
    """A desktop-wallpaper-like gradient so the transparent window shows."""
    pm = QPixmap(width + 2 * PAD, height + 2 * PAD)
    grad = QLinearGradient(QPointF(0, 0), QPointF(pm.width(), pm.height()))
    grad.setColorAt(0.0, QColor("#3d5a80"))
    grad.setColorAt(1.0, QColor("#98c1d9"))
    p = QPainter(pm)
    p.fillRect(QRectF(pm.rect()), grad)
    p.end()
    return pm


def _on_backdrop(window: OverlayWindow) -> QPixmap:
    image = _backdrop(window.width(), window.height())
    p = QPainter(image)
    p.drawPixmap(PAD, PAD, window.grab())
    p.end()
    return image


def _overlay(app: QApplication, specs, style: str, layout: str, main_key: str,
             scale: float = 1.0) -> OverlayWindow:
    window = OverlayWindow(specs, style)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.set_layout(layout, [s.key for s in specs], main_key)
    window.set_scale(scale)
    window.show()                           # off-screen; lays out the gauges
    app.processEvents()
    return window


def _close(window: OverlayWindow) -> None:
    window.allow_close()
    window.close()


def make_pngs(app: QApplication, specs) -> None:
    for name, style, layout, main_key in SHOTS:
        window = _overlay(app, specs, style, layout, main_key)
        window.apply_readings(SNAPSHOT, snap=True)
        _on_backdrop(window).save(str(OUT_DIR / name))
        print("wrote", OUT_DIR / name)
        _close(window)


class _DialogStub:
    """Just enough of Controller for SettingsDialog to render."""

    def __init__(self, specs) -> None:
        self.settings = Settings()
        self.specs = specs

    def __getattr__(self, name):
        return lambda *args: True


def make_settings_shot(app: QApplication, specs) -> None:
    dialog = SettingsDialog(_DialogStub(specs))
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(OUT_DIR / "settings.png"))
    print("wrote", OUT_DIR / "settings.png")
    dialog.close()


def make_gifs(app: QApplication, specs) -> None:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed - skipping GIFs")
        return
    demo = DemoProvider()
    for name, style, scale, colors in GIFS:
        window = _overlay(app, specs, style, "dashboard", "cpu", scale)
        frames = []
        for i in range(GIF_FRAMES):
            window.apply_readings(demo.poll_at(i * GIF_DEMO_SECONDS / GIF_FRAMES), snap=True)
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            _on_backdrop(window).save(buf, "PNG")
            frame = Image.open(io.BytesIO(bytes(buf.data()))).convert("RGB")
            frames.append(frame.quantize(colors=colors, method=Image.Quantize.MEDIANCUT))
        path = OUT_DIR / name
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=GIF_FRAME_MS, loop=0, optimize=True)
        print(f"wrote {path} ({path.stat().st_size // 1024} KB)")
        _close(window)


def main() -> int:
    app = QApplication(sys.argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    specs = DemoProvider().metrics()
    make_pngs(app, specs)
    make_settings_shot(app, specs)
    make_gifs(app, specs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
