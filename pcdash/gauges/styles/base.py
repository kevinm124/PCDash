"""Gauge style interface and shared drawing helpers.

A style draws a gauge in two layers:

* ``paint_background`` - everything that never changes for a given size
  (bezel, face, ticks, numbers, redline). It is rendered once into a cached
  pixmap, so it can be as detailed as you like.
* ``paint_foreground`` - the parts that move: needle/arc, digital readout,
  detail text, warning lamp. This runs on every animation frame, so keep it
  light.

Each layer is split by gauge kind (``MetricSpec.kind``): a round *dial*
(tachometer) or a *fuel* gauge. To add a style, subclass ``GaugeStyle`` in a
new module, implement the four ``paint_*`` methods and register it in
``pcdash/gauges/styles/__init__.py``.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter

from ...providers.base import FUEL, MetricSpec

# Dial geometry, in Qt's math convention: degrees counter-clockwise from
# 3 o'clock. The dial starts bottom-left (225 deg) and sweeps 270 deg clockwise.
START_ANGLE = 225.0
SWEEP = 270.0

# Fuel gauge: a 100 deg arc across the top, pivoting below the centre.
FUEL_START = 140.0
FUEL_SWEEP = 100.0
FUEL_PIVOT = 0.40      # pivot offset below the centre, as a fraction of radius


@dataclass(frozen=True)
class GaugeState:
    """Dynamic values passed to ``paint_foreground``."""

    value: float          # animated (displayed) value
    detail: str           # secondary text from the provider
    warning: bool         # warning lamp on/off


class GaugeStyle(ABC):
    key: str = "base"     # id used in the config file
    name: str = "Base"    # human-readable name for menus

    def paint_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        """Draw the static layer (called rarely, result is cached)."""
        if spec.kind == FUEL:
            self.paint_fuel_background(p, rect, spec)
        else:
            self.paint_dial_background(p, rect, spec)

    def paint_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                         state: GaugeState) -> None:
        """Draw the moving layer (called every animation frame)."""
        if spec.kind == FUEL:
            self.paint_fuel_foreground(p, rect, spec, state)
        else:
            self.paint_dial_foreground(p, rect, spec, state)

    @abstractmethod
    def paint_dial_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None: ...

    @abstractmethod
    def paint_dial_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                              state: GaugeState) -> None: ...

    @abstractmethod
    def paint_fuel_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None: ...

    @abstractmethod
    def paint_fuel_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                              state: GaugeState) -> None: ...


# --- geometry helpers ------------------------------------------------------

def square(rect: QRectF) -> QRectF:
    """Largest square centred in ``rect``."""
    side = min(rect.width(), rect.height())
    return QRectF(
        rect.center().x() - side / 2, rect.center().y() - side / 2, side, side
    )


def angle_for(fraction: float, start: float = START_ANGLE, sweep: float = SWEEP) -> float:
    """Dial angle (degrees, Qt math convention) for a 0..1 fraction."""
    return start - sweep * fraction


def fuel_angle(fraction: float) -> float:
    return angle_for(fraction, FUEL_START, FUEL_SWEEP)


def fuel_pivot(center: QPointF, radius: float) -> QPointF:
    return QPointF(center.x(), center.y() + radius * FUEL_PIVOT)


def fuel_label(fraction: float) -> str:
    """E / ½ / F markings for a fuel gauge (empty for other ticks)."""
    return {0.0: "E", 0.5: "½", 1.0: "F"}.get(round(fraction, 3), "")


def point_at(center: QPointF, radius: float, angle_deg: float) -> QPointF:
    rad = math.radians(angle_deg)
    return QPointF(center.x() + radius * math.cos(rad),
                   center.y() - radius * math.sin(rad))


def circle_rect(center: QPointF, radius: float) -> QRectF:
    return QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)


def draw_arc(p: QPainter, center: QPointF, radius: float, frac_from: float,
             frac_to: float, start: float = START_ANGLE, sweep: float = SWEEP) -> None:
    """Stroke the arc between two 0..1 fractions with the current pen."""
    a = start - sweep * frac_from
    span = -sweep * (frac_to - frac_from)
    p.drawArc(circle_rect(center, radius), int(a * 16), int(span * 16))


# --- text helpers ----------------------------------------------------------

MIN_FONT_PX = 9     # keep small gauges readable


def make_font(family: str, pixel_size: float, weight: QFont.Weight = QFont.Weight.Normal,
              italic: bool = False) -> QFont:
    font = QFont(family)
    font.setPixelSize(max(MIN_FONT_PX, int(round(pixel_size))))
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
