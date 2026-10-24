"""Gauge style interface and shared drawing helpers.

A style draws a gauge in two layers:

* ``paint_background`` - everything that never changes for a given size
  (bezel, face, ticks, numbers, redline). It is rendered once into a cached
  pixmap, so it can be as detailed as you like.
* ``paint_foreground`` - the parts that move: needle/arc, digital readout,
  detail text, warning lamp. This runs on every animation frame, so keep it
  light.

To add a style, subclass ``GaugeStyle`` in a new module and register it in
``pcdash/gauges/styles/__init__.py``.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from ...providers.base import MetricSpec

# Dial geometry, in Qt's math convention: degrees counter-clockwise from
# 3 o'clock. The dial starts bottom-left (225 deg) and sweeps 270 deg clockwise.
START_ANGLE = 225.0
SWEEP = 270.0


@dataclass(frozen=True)
class GaugeState:
    """Dynamic values passed to ``paint_foreground``."""

    value: float          # animated (displayed) value
    detail: str           # secondary text from the provider
    warning: bool         # warning lamp on/off


class GaugeStyle(ABC):
    key: str = "base"     # id used in the config file
    name: str = "Base"    # human-readable name for menus

    @abstractmethod
    def paint_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        """Draw the static layer (called rarely, result is cached)."""

    @abstractmethod
    def paint_foreground(
        self, p: QPainter, rect: QRectF, spec: MetricSpec, state: GaugeState
    ) -> None:
        """Draw the moving layer (called every animation frame)."""


# --- geometry helpers ------------------------------------------------------

def square(rect: QRectF) -> QRectF:
    """Largest square centred in ``rect``."""
    side = min(rect.width(), rect.height())
    return QRectF(
        rect.center().x() - side / 2, rect.center().y() - side / 2, side, side
    )


def angle_for(fraction: float) -> float:
    """Dial angle (degrees, Qt math convention) for a 0..1 fraction."""
    return START_ANGLE - SWEEP * fraction


def point_at(center: QPointF, radius: float, angle_deg: float) -> QPointF:
    rad = math.radians(angle_deg)
    return QPointF(center.x() + radius * math.cos(rad),
                   center.y() - radius * math.sin(rad))


def circle_rect(center: QPointF, radius: float) -> QRectF:
    return QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)


def draw_arc(p: QPainter, center: QPointF, radius: float,
             frac_from: float, frac_to: float) -> None:
    """Stroke the dial arc between two 0..1 fractions with the current pen."""
    start = angle_for(frac_from)
    span = -SWEEP * (frac_to - frac_from)
    p.drawArc(circle_rect(center, radius), int(start * 16), int(span * 16))


# --- text helpers ----------------------------------------------------------

def make_font(family: str, pixel_size: float, weight: QFont.Weight = QFont.Weight.Normal,
              italic: bool = False) -> QFont:
    font = QFont(family)
    font.setPixelSize(max(1, int(round(pixel_size))))
    font.setWeight(weight)
    font.setItalic(italic)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def draw_text(p: QPainter, center: QPointF, text: str, font: QFont,
              color: QColor) -> None:
    """Draw ``text`` centred on ``center``."""
    p.setFont(font)
    p.setPen(color)
    size = font.pixelSize() * 2.0
    box = QRectF(center.x() - size * 10, center.y() - size, size * 20, size * 2)
    p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)


def format_tick(value: float) -> str:
    return str(int(round(value))) if abs(value - round(value)) < 1e-6 else f"{value:.1f}"
