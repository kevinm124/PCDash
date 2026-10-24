"""Sporty style: dark carbon face, white ticks, red needle and redline."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                           QPen, QPolygonF, QRadialGradient)

from ...providers.base import MetricSpec
from .base import (FUEL_START, FUEL_SWEEP, GaugeState, GaugeStyle, angle_for,
                   draw_arc, draw_text, format_tick, fuel_angle, fuel_label,
                   fuel_pivot, make_font, point_at, square)

FONT = "Bahnschrift"          # DIN-like, ships with Windows 10+
RED = QColor("#ff2a1a")
REDLINE = QColor("#d81b12")
TICK = QColor("#ececec")
TICK_MINOR = QColor("#8c8c8c")
TEXT_DIM = QColor("#9a9ea4")


class SportyStyle(GaugeStyle):
    key = "sporty"
    name = "Sporty"

    # --- shared parts ------------------------------------------------------

    @staticmethod
    def _bezel_and_face(p: QPainter, s: QRectF) -> None:
        c, r = s.center(), s.width() / 2
        bezel = QLinearGradient(s.topLeft(), s.bottomRight())
        bezel.setColorAt(0.0, QColor("#4a4d52"))
        bezel.setColorAt(0.5, QColor("#16181b"))
        bezel.setColorAt(1.0, QColor("#2e3135"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bezel))
        p.drawEllipse(c, r * 0.99, r * 0.99)

        face = QRadialGradient(c, r * 0.92)
        face.setColorAt(0.0, QColor("#24272c"))
        face.setColorAt(0.85, QColor("#0e0f11"))
        face.setColorAt(1.0, QColor("#050506"))
        p.setBrush(QBrush(face))
        p.drawEllipse(c, r * 0.92, r * 0.92)

    @staticmethod
    def _tick(p: QPainter, pivot: QPointF, ang: float, inner: float, outer: float,
              color: QColor, width: float) -> None:
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.drawLine(point_at(pivot, inner, ang), point_at(pivot, outer, ang))

    @staticmethod
    def _needle(p: QPainter, pivot: QPointF, ang: float, length: float,
                tail: float, width: float) -> None:
        blade = QPolygonF([
            QPointF(-tail, -width), QPointF(length * 0.95, -width * 0.25),
            QPointF(length, 0.0), QPointF(length * 0.95, width * 0.25),
            QPointF(-tail, width),
        ])
        p.save()
        p.translate(pivot)
        p.rotate(-ang)
        p.setPen(QPen(QColor(255, 40, 20, 70), width * 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(blade)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(RED)
        p.drawPolygon(blade)
        p.restore()

    @staticmethod
    def _hub(p: QPainter, pivot: QPointF, radius: float) -> None:
        hub = QRadialGradient(QPointF(pivot.x() - radius * 0.3, pivot.y() - radius * 0.3),
                              radius * 1.2)
        hub.setColorAt(0.0, QColor("#5a5d62"))
        hub.setColorAt(1.0, QColor("#111214"))
        p.setPen(QPen(QColor("#000000"), radius * 0.13))
        p.setBrush(QBrush(hub))
        p.drawEllipse(pivot, radius, radius)

    @staticmethod
    def _lamp(p: QPainter, center: QPointF, radius: float, on: bool) -> None:
        if on:
            glow = QRadialGradient(center, radius * 2.6)
            glow.setColorAt(0.0, QColor(255, 60, 30, 200))
            glow.setColorAt(1.0, QColor(255, 60, 30, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(center, radius * 2.6, radius * 2.6)
            p.setBrush(QColor("#ff4a2a"))
        else:
            p.setPen(QPen(QColor("#3a3c40"), radius * 0.16))
            p.setBrush(QColor("#2a1410"))
        p.drawEllipse(center, radius, radius)

    # --- dial (tachometer) -------------------------------------------------

    def paint_dial_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        self._bezel_and_face(p, s)

        if spec.red_zone is not None:
            pen = QPen(REDLINE, r * 0.075)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            draw_arc(p, c, r * 0.805, spec.fraction(spec.red_zone[0]),
                     spec.fraction(spec.red_zone[1]))

        total = spec.major_ticks * spec.minor_ticks
        span = spec.maximum - spec.minimum
        number_font = make_font(FONT, r * 0.105, QFont.Weight.DemiBold)
        for i in range(total + 1):
            frac = i / total
            value = spec.minimum + frac * span
            ang = angle_for(frac)
            red = spec.in_red_zone(value)
            if i % spec.minor_ticks == 0:
                color = REDLINE.lighter(130) if red else TICK
                self._tick(p, c, ang, r * 0.70, r * 0.845, color, r * 0.024)
                draw_text(p, point_at(c, r * 0.575, ang), format_tick(value),
                          number_font, color)
            else:
                self._tick(p, c, ang, r * 0.78, r * 0.845,
                           REDLINE if red else TICK_MINOR, r * 0.010)

        draw_text(p, QPointF(c.x(), c.y() - r * 0.30), spec.label,
                  make_font(FONT, r * 0.13, QFont.Weight.Bold, italic=True), TICK)

    def paint_dial_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                              state: GaugeState) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2

        draw_text(p, QPointF(c.x(), c.y() + r * 0.36), f"{state.value:.0f}{spec.unit}",
                  make_font(FONT, r * 0.19, QFont.Weight.Bold), TICK)
        if state.detail:
            draw_text(p, QPointF(c.x(), c.y() + r * 0.54), state.detail,
                      make_font(FONT, r * 0.08), TEXT_DIM)
        self._lamp(p, QPointF(c.x(), c.y() + r * 0.76), r * 0.05, state.warning)
        self._needle(p, c, angle_for(spec.fraction(state.value)), r * 0.84,
                     r * 0.14, r * 0.028)
        self._hub(p, c, r * 0.075)

    # --- fuel gauge --------------------------------------------------------

    def paint_fuel_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        pivot = fuel_pivot(c, r)
        self._bezel_and_face(p, s)

        if spec.red_zone is not None:
            pen = QPen(REDLINE, r * 0.08)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            draw_arc(p, pivot, r * 0.96, spec.fraction(spec.red_zone[0]),
                     spec.fraction(spec.red_zone[1]), FUEL_START, FUEL_SWEEP)

        total = spec.major_ticks * spec.minor_ticks
        label_font = make_font(FONT, r * 0.15, QFont.Weight.Bold)
        for i in range(total + 1):
            frac = i / total
            ang = fuel_angle(frac)
            red = spec.in_red_zone(spec.minimum + frac * (spec.maximum - spec.minimum))
            if i % spec.minor_ticks == 0:
                color = REDLINE.lighter(130) if red else TICK
                self._tick(p, pivot, ang, r * 0.84, r * 1.0, color, r * 0.03)
                if text := fuel_label(frac):
                    draw_text(p, point_at(pivot, r * 0.70, ang), text, label_font, color)
            else:
                self._tick(p, pivot, ang, r * 0.91, r * 1.0,
                           REDLINE if red else TICK_MINOR, r * 0.014)

        draw_text(p, QPointF(c.x(), c.y() + r * 0.64), spec.label,
                  make_font(FONT, r * 0.15, QFont.Weight.Bold, italic=True), TICK)

    def paint_fuel_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                              state: GaugeState) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        pivot = fuel_pivot(c, r)

        self._lamp(p, QPointF(c.x() - r * 0.45, pivot.y()), r * 0.06, state.warning)
        draw_text(p, QPointF(c.x() + r * 0.45, pivot.y()), f"{state.value:.0f}%",
                  make_font(FONT, r * 0.12, QFont.Weight.Bold), TICK)
        if state.detail:
            draw_text(p, QPointF(c.x(), c.y() + r * 0.79), state.detail,
                      make_font(FONT, r * 0.09), TEXT_DIM)
        self._needle(p, pivot, fuel_angle(spec.fraction(state.value)), r * 0.92,
                     r * 0.12, r * 0.04)
        self._hub(p, pivot, r * 0.09)
