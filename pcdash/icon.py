"""App/tray icon, drawn in code so the repo needs no binary assets."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def _render(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = size / 2
    c = QPointF(r, r)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#2b2e33"))
    p.drawEllipse(c, r * 0.98, r * 0.98)
    p.setBrush(QColor("#0d0e10"))
    p.drawEllipse(c, r * 0.84, r * 0.84)

    arc = QRectF(r * 0.36, r * 0.36, r * 1.28, r * 1.28)
    pen = QPen(QColor("#e8e8e8"), max(1.0, r * 0.16))
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    p.setPen(pen)
    p.drawArc(arc, 225 * 16, -200 * 16)
    pen.setColor(QColor("#e0261a"))
    p.setPen(pen)
    p.drawArc(arc, 25 * 16, -70 * 16)

    needle = QPen(QColor("#ff3b25"), max(1.5, r * 0.14))
    needle.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(needle)
    p.drawLine(c, QPointF(r * 1.55, r * 0.62))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#9a9da2"))
    p.drawEllipse(c, r * 0.14, r * 0.14)
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 256):
        icon.addPixmap(_render(size))
    return icon
