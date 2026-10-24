"""Retro style: cream face, black serif numbers, chrome bezel, thin needle."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont,
                           QLinearGradient, QPainter, QPen, QPolygonF,
                           QRadialGradient)

from ...providers.base import MetricSpec
from .base import (FUEL_START, FUEL_SWEEP, GaugeState, GaugeStyle, angle_for,
                   draw_arc, draw_text, format_tick, fuel_angle, fuel_label,
                   fuel_pivot, make_font, point_at, square)

SERIF = "Georgia"
MONO = "Consolas"
INK = QColor("#1b1b1b")
INK_SOFT = QColor("#4a463e")
RED = QColor("#b3261e")
AMBER = QColor("#ffb000")


class RetroStyle(GaugeStyle):
    key = "retro"
    name = "Retro"

    # --- shared parts ------------------------------------------------------

    @staticmethod
    def _bezel_and_face(p: QPainter, s: QRectF) -> None:
        c, r = s.center(), s.width() / 2
        chrome = QConicalGradient(c, 45)
        for pos, color in ((0.0, "#f7f7f7"), (0.15, "#8d8f93"), (0.3, "#fdfdfd"),
                           (0.5, "#6c6e72"), (0.65, "#e9e9ea"), (0.8, "#7d7f83"),
                           (1.0, "#f7f7f7")):
            chrome.setColorAt(pos, QColor(color))
        p.setPen(QPen(QColor("#3c3c3c"), r * 0.01))
        p.setBrush(QBrush(chrome))
        p.drawEllipse(c, r * 0.985, r * 0.985)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#2a2a2a"))
        p.drawEllipse(c, r * 0.905, r * 0.905)

        face = QRadialGradient(QPointF(c.x(), c.y() - r * 0.2), r * 1.1)
        face.setColorAt(0.0, QColor("#fffaf0"))
        face.setColorAt(0.7, QColor("#f1e8d0"))
        face.setColorAt(1.0, QColor("#d9cdaa"))
        p.setBrush(QBrush(face))
        p.drawEllipse(c, r * 0.89, r * 0.89)

    @staticmethod
    def _glass(p: QPainter, s: QRectF) -> None:
        """Soft reflection across the top of the glass."""
        c, r = s.center(), s.width() / 2
        shine = QLinearGradient(QPointF(c.x(), c.y() - r * 0.9), QPointF(c.x(), c.y()))
        shine.setColorAt(0.0, QColor(255, 255, 255, 70))
        shine.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(shine))
        p.drawEllipse(QRectF(c.x() - r * 0.75, c.y() - r * 0.88, r * 1.5, r * 0.95))

    @staticmethod
    def _tick(p: QPainter, pivot: QPointF, ang: float, inner: float, outer: float,
              color: QColor, width: float) -> None:
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.drawLine(point_at(pivot, inner, ang), point_at(pivot, outer, ang))

    @staticmethod
    def _needle(p: QPainter, pivot: QPointF, ang: float, length: float, r: float) -> None:
        w = r * 0.014
        blade = QPolygonF([QPointF(-r * 0.10, -w), QPointF(length, -w * 0.3),
                           QPointF(length, w * 0.3), QPointF(-r * 0.10, w)])
        p.save()
        p.translate(pivot)
        p.rotate(-ang)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 45))                     # drop shadow
        p.drawPolygon(blade.translated(r * 0.012, r * 0.02))
        p.setBrush(INK)
        p.drawPolygon(blade)
        p.drawEllipse(QPointF(-r * 0.10, 0), r * 0.04, r * 0.04)  # counterweight
        p.restore()

        hub = QRadialGradient(QPointF(pivot.x() - r * 0.015, pivot.y() - r * 0.015), r * 0.06)
        hub.setColorAt(0.0, QColor("#ffffff"))
        hub.setColorAt(1.0, QColor("#7b7d81"))
        p.setPen(QPen(QColor("#3c3c3c"), r * 0.006))
        p.setBrush(QBrush(hub))
        p.drawEllipse(pivot, r * 0.05, r * 0.05)

    @staticmethod
    def _lamp(p: QPainter, center: QPointF, radius: float, on: bool) -> None:
        p.setPen(QPen(QColor("#6d6f73"), radius * 0.3))     # chrome rim
        if on:
            glow = QRadialGradient(center, radius * 2.4)
            glow.setColorAt(0.0, QColor(255, 176, 0, 170))
            glow.setColorAt(1.0, QColor(255, 176, 0, 0))
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(center, radius * 2.4, radius * 2.4)
            p.restore()
            jewel = QRadialGradient(center, radius)
            jewel.setColorAt(0.0, QColor("#fff3c4"))
            jewel.setColorAt(1.0, AMBER)
        else:
            jewel = QRadialGradient(center, radius)
            jewel.setColorAt(0.0, QColor("#a38c5c"))
            jewel.setColorAt(1.0, QColor("#5e4c2a"))
        p.setBrush(QBrush(jewel))
        p.drawEllipse(center, radius, radius)

    @staticmethod
    def _odometer_box(s: QRectF) -> QRectF:
        c, r = s.center(), s.width() / 2
        return QRectF(c.x() - r * 0.24, c.y() + r * 0.30, r * 0.48, r * 0.17)

    # --- dial --------------------------------------------------------------

    def paint_dial_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        self._bezel_and_face(p, s)

        if spec.red_zone is not None:
            pen = QPen(RED, r * 0.04)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            draw_arc(p, c, r * 0.835, spec.fraction(spec.red_zone[0]),
                     spec.fraction(spec.red_zone[1]))

        total = spec.major_ticks * spec.minor_ticks
        span = spec.maximum - spec.minimum
        number_font = make_font(SERIF, r * 0.115)
        for i in range(total + 1):
            frac = i / total
            value = spec.minimum + frac * span
            ang = angle_for(frac)
            color = RED if spec.in_red_zone(value) else INK
            if i % spec.minor_ticks == 0:
                self._tick(p, c, ang, r * 0.71, r * 0.855, color, r * 0.018)
                draw_text(p, point_at(c, r * 0.585, ang), format_tick(value),
                          number_font, color)
            else:
                self._tick(p, c, ang, r * 0.79, r * 0.855, color, r * 0.007)

        draw_text(p, QPointF(c.x(), c.y() - r * 0.30), spec.label,
                  make_font(SERIF, r * 0.11, italic=True), INK_SOFT)

        box = self._odometer_box(s)
        p.setPen(QPen(QColor("#8a8170"), r * 0.012))
        p.setBrush(QColor("#151515"))
        p.drawRoundedRect(box, r * 0.02, r * 0.02)
        self._glass(p, s)

    def paint_dial_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                              state: GaugeState) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2

        box = self._odometer_box(s)
        draw_text(p, box.center(), f"{state.value:.0f}{spec.unit}",
                  make_font(MONO, r * 0.12, QFont.Weight.Bold), QColor("#f4efe2"))
        if state.detail:
            draw_text(p, QPointF(c.x(), c.y() + r * 0.57), state.detail,
                      make_font(SERIF, r * 0.08, italic=True), INK_SOFT)
        self._lamp(p, QPointF(c.x(), c.y() + r * 0.75), r * 0.045, state.warning)
        self._needle(p, c, angle_for(spec.fraction(state.value)), r * 0.84, r)

    # --- fuel gauge --------------------------------------------------------

    def paint_fuel_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        pivot = fuel_pivot(c, r)
        self._bezel_and_face(p, s)

        if spec.red_zone is not None:
            pen = QPen(RED, r * 0.045)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            draw_arc(p, pivot, r * 0.97, spec.fraction(spec.red_zone[0]),
                     spec.fraction(spec.red_zone[1]), FUEL_START, FUEL_SWEEP)

        total = spec.major_ticks * spec.minor_ticks
        label_font = make_font(SERIF, r * 0.16, QFont.Weight.Bold)
        for i in range(total + 1):
            frac = i / total
            ang = fuel_angle(frac)
            red = spec.in_red_zone(spec.minimum + frac * (spec.maximum - spec.minimum))
            color = RED if red else INK
            if i % spec.minor_ticks == 0:
                self._tick(p, pivot, ang, r * 0.85, r * 1.0, color, r * 0.024)
                if text := fuel_label(frac):
                    draw_text(p, point_at(pivot, r * 0.70, ang), text, label_font, color)
            else:
                self._tick(p, pivot, ang, r * 0.92, r * 1.0, color, r * 0.012)

        draw_text(p, QPointF(c.x(), c.y() + r * 0.64), spec.label,
                  make_font(SERIF, r * 0.15, italic=True), INK_SOFT)
        self._glass(p, s)

    def paint_fuel_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                              state: GaugeState) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        pivot = fuel_pivot(c, r)

        self._lamp(p, QPointF(c.x() - r * 0.45, pivot.y()), r * 0.06, state.warning)
        draw_text(p, QPointF(c.x() + r * 0.45, pivot.y()), f"{state.value:.0f}%",
                  make_font(SERIF, r * 0.12, QFont.Weight.Bold), INK)
        if state.detail:
            draw_text(p, QPointF(c.x(), c.y() + r * 0.78), state.detail,
                      make_font(SERIF, r * 0.09, italic=True), INK_SOFT)
        self._needle(p, pivot, fuel_angle(spec.fraction(state.value)), r * 0.92, r)
