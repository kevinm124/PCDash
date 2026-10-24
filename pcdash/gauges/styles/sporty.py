"""Sporty style: dark carbon face, white ticks, red needle and redline."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                           QPen, QPolygonF, QRadialGradient)

from ...providers.base import MetricSpec
from .base import (GaugeState, GaugeStyle, angle_for, draw_arc, draw_text,
                   format_tick, make_font, point_at, square)

FONT = "Bahnschrift"          # DIN-like, ships with Windows 10+
RED = QColor("#ff2a1a")
REDLINE = QColor("#d81b12")
TICK = QColor("#ececec")
TICK_MINOR = QColor("#8c8c8c")
TEXT_DIM = QColor("#9a9ea4")


class SportyStyle(GaugeStyle):
    key = "sporty"
    name = "Sporty"

    def paint_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        s = square(rect)
        c = s.center()
        r = s.width() / 2

        # Bezel: brushed dark metal ring.
        bezel = QLinearGradient(s.topLeft(), s.bottomRight())
        bezel.setColorAt(0.0, QColor("#4a4d52"))
        bezel.setColorAt(0.5, QColor("#16181b"))
        bezel.setColorAt(1.0, QColor("#2e3135"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bezel))
        p.drawEllipse(c, r * 0.99, r * 0.99)

        # Face.
        face = QRadialGradient(c, r * 0.92)
        face.setColorAt(0.0, QColor("#24272c"))
        face.setColorAt(0.85, QColor("#0e0f11"))
        face.setColorAt(1.0, QColor("#050506"))
        p.setBrush(QBrush(face))
        p.drawEllipse(c, r * 0.92, r * 0.92)

        # Redline band along the outer edge.
        if spec.redline is not None:
            pen = QPen(REDLINE, r * 0.075)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            draw_arc(p, c, r * 0.805, spec.fraction(spec.redline), 1.0)

        # Ticks and numbers.
        total = spec.major_ticks * spec.minor_ticks
        span = spec.maximum - spec.minimum
        number_font = make_font(FONT, r * 0.105, QFont.Weight.DemiBold)
        for i in range(total + 1):
            frac = i / total
            value = spec.minimum + frac * span
            ang = angle_for(frac)
            major = i % spec.minor_ticks == 0
            in_red = spec.redline is not None and value >= spec.redline - 1e-9
            if major:
                color = REDLINE.lighter(130) if in_red else TICK
                width, inner = r * 0.024, r * 0.70
            else:
                color = REDLINE if in_red else TICK_MINOR
                width, inner = r * 0.010, r * 0.78
            pen = QPen(color, width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawLine(point_at(c, inner, ang), point_at(c, r * 0.845, ang))
            if major:
                draw_text(p, point_at(c, r * 0.575, ang), format_tick(value),
                          number_font, color)

        # Gauge label.
        draw_text(p, QPointF(c.x(), c.y() - r * 0.30), spec.label,
                  make_font(FONT, r * 0.13, QFont.Weight.Bold, italic=True), TICK)

    def paint_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                         state: GaugeState) -> None:
        s = square(rect)
        c = s.center()
        r = s.width() / 2

        # Digital readout and detail line.
        draw_text(p, QPointF(c.x(), c.y() + r * 0.36), f"{state.value:.0f}{spec.unit}",
                  make_font(FONT, r * 0.19, QFont.Weight.Bold), TICK)
        if state.detail:
            draw_text(p, QPointF(c.x(), c.y() + r * 0.54), state.detail,
                      make_font(FONT, r * 0.075), TEXT_DIM)

        # Warning lamp in the gap at the bottom of the dial.
        lamp_c = QPointF(c.x(), c.y() + r * 0.76)
        lamp_r = r * 0.05
        if state.warning:
            glow = QRadialGradient(lamp_c, lamp_r * 2.6)
            glow.setColorAt(0.0, QColor(255, 60, 30, 200))
            glow.setColorAt(1.0, QColor(255, 60, 30, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(lamp_c, lamp_r * 2.6, lamp_r * 2.6)
            p.setBrush(QColor("#ff4a2a"))
        else:
            p.setPen(QPen(QColor("#3a3c40"), r * 0.008))
            p.setBrush(QColor("#2a1410"))
        p.drawEllipse(lamp_c, lamp_r, lamp_r)

        # Needle: tapered red blade with a soft glow.
        ang = angle_for(spec.fraction(state.value))
        w = r * 0.028
        blade = QPolygonF([
            QPointF(-r * 0.14, -w), QPointF(r * 0.80, -w * 0.25),
            QPointF(r * 0.84, 0.0), QPointF(r * 0.80, w * 0.25),
            QPointF(-r * 0.14, w),
        ])
        p.save()
        p.translate(c)
        p.rotate(-ang)
        p.setPen(QPen(QColor(255, 40, 20, 70), w * 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(blade)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(RED)
        p.drawPolygon(blade)
        p.restore()

        # Hub cap.
        hub = QRadialGradient(QPointF(c.x() - r * 0.02, c.y() - r * 0.02), r * 0.09)
        hub.setColorAt(0.0, QColor("#5a5d62"))
        hub.setColorAt(1.0, QColor("#111214"))
        p.setPen(QPen(QColor("#000000"), r * 0.01))
        p.setBrush(QBrush(hub))
        p.drawEllipse(c, r * 0.075, r * 0.075)
