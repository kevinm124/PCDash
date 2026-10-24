"""Futuristic style: EV-like digital cluster. Glowing segmented neon arcs and
big digital numbers, no physical needle. Drives are shown as battery bars."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QPen, QPolygonF,
                           QRadialGradient)

from ...providers.base import MetricSpec
from .base import GaugeState, GaugeStyle, draw_arc, draw_text, make_font, square

FONT = "Segoe UI"
CYAN = QColor("#00e5ff")
VIOLET = QColor("#b14dff")
HOT = QColor("#ff2d55")
TEXT = QColor("#eafcff")
TEXT_DIM = QColor("#6fb7c4")

SEGMENTS = 36          # dial arc segments
SEG_FILL = 0.72        # fraction of each segment slot that is lit (rest is gap)
CELLS = 10             # battery cells for drives


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor.fromRgbF(a.redF() + (b.redF() - a.redF()) * t,
                           a.greenF() + (b.greenF() - a.greenF()) * t,
                           a.blueF() + (b.blueF() - a.blueF()) * t)


def _alpha(color: QColor, alpha: int) -> QColor:
    c = QColor(color)
    c.setAlpha(alpha)
    return c


class FuturisticStyle(GaugeStyle):
    key = "futuristic"
    name = "Futuristic"

    # --- shared parts ------------------------------------------------------

    @staticmethod
    def _disc(p: QPainter, s: QRectF) -> None:
        c, r = s.center(), s.width() / 2
        bg = QRadialGradient(c, r * 0.95)
        bg.setColorAt(0.0, QColor(10, 24, 40, 225))
        bg.setColorAt(1.0, QColor(3, 8, 16, 235))
        p.setPen(QPen(_alpha(CYAN, 110), r * 0.012))
        p.setBrush(QBrush(bg))
        p.drawEllipse(c, r * 0.95, r * 0.95)
        p.setPen(QPen(_alpha(CYAN, 35), r * 0.006))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, r * 0.89, r * 0.89)

    @staticmethod
    def _segment_color(spec: MetricSpec, frac: float) -> QColor:
        value = spec.minimum + frac * (spec.maximum - spec.minimum)
        return HOT if spec.in_red_zone(value) else _mix(CYAN, VIOLET, frac)

    @staticmethod
    def _warning_sign(p: QPainter, center: QPointF, size: float, on: bool) -> None:
        tri = QPolygonF([QPointF(center.x(), center.y() - size * 0.55),
                         QPointF(center.x() + size * 0.62, center.y() + size * 0.5),
                         QPointF(center.x() - size * 0.62, center.y() + size * 0.5)])
        if on:
            p.setPen(QPen(_alpha(HOT, 90), size * 0.35))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolygon(tri)
            p.setPen(QPen(HOT, size * 0.1))
            p.setBrush(_alpha(HOT, 60))
        else:
            p.setPen(QPen(_alpha(TEXT_DIM, 40), size * 0.08))
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(tri)

    # --- dial: segmented neon arc ------------------------------------------

    @staticmethod
    def _draw_segment(p: QPainter, c: QPointF, radius: float, index: int,
                      amount: float = 1.0) -> None:
        start = index / SEGMENTS
        draw_arc(p, c, radius, start, start + SEG_FILL * amount / SEGMENTS)

    def paint_dial_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        self._disc(p, s)

        # Unlit track.
        for i in range(SEGMENTS):
            color = self._segment_color(spec, (i + 0.5) / SEGMENTS)
            pen = QPen(_alpha(color, 38), r * 0.10)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            self._draw_segment(p, c, r * 0.78, i)

        draw_text(p, QPointF(c.x(), c.y() - r * 0.33), spec.label.upper(),
                  make_font(FONT, r * 0.10, QFont.Weight.DemiBold), TEXT_DIM)
        small = make_font(FONT, r * 0.07)
        draw_text(p, QPointF(c.x() - r * 0.50, c.y() + r * 0.72),
                  f"{spec.minimum:.0f}", small, TEXT_DIM)
        draw_text(p, QPointF(c.x() + r * 0.50, c.y() + r * 0.72),
                  f"{spec.maximum:.0f}", small, TEXT_DIM)

    def paint_dial_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                              state: GaugeState) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        lit = spec.fraction(state.value) * SEGMENTS
        full = int(lit)

        glow_w, core_w = r * 0.16, r * 0.10
        for i in range(min(SEGMENTS, math.ceil(lit))):
            amount = 1.0 if i < full else lit - full
            color = self._segment_color(spec, (i + 0.5) / SEGMENTS)
            for width, alpha in ((glow_w, 55), (core_w, 255)):
                pen = QPen(_alpha(color, alpha), width)
                pen.setCapStyle(Qt.PenCapStyle.FlatCap)
                p.setPen(pen)
                self._draw_segment(p, c, r * 0.78, i, amount)

        color = HOT if state.warning else TEXT
        draw_text(p, QPointF(c.x(), c.y() + r * 0.02), f"{state.value:.0f}",
                  make_font(FONT, r * 0.34, QFont.Weight.Light), color)
        draw_text(p, QPointF(c.x(), c.y() + r * 0.27), spec.unit,
                  make_font(FONT, r * 0.09, QFont.Weight.DemiBold), _alpha(CYAN, 200))
        if state.detail:
            draw_text(p, QPointF(c.x(), c.y() + r * 0.45), state.detail,
                      make_font(FONT, r * 0.08), TEXT_DIM)
        self._warning_sign(p, QPointF(c.x(), c.y() + r * 0.70), r * 0.11, state.warning)

    # --- drives: battery bar -----------------------------------------------

    @staticmethod
    def _battery_rect(s: QRectF) -> QRectF:
        c, r = s.center(), s.width() / 2
        return QRectF(c.x() - r * 0.56, c.y() + r * 0.06, r * 1.06, r * 0.28)

    def paint_fuel_background(self, p: QPainter, rect: QRectF, spec: MetricSpec) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        self._disc(p, s)

        body = self._battery_rect(s)
        p.setPen(QPen(_alpha(CYAN, 150), r * 0.02))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body, r * 0.04, r * 0.04)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_alpha(CYAN, 150))
        p.drawRoundedRect(QRectF(body.right() + r * 0.015, body.center().y() - r * 0.06,
                                 r * 0.05, r * 0.12), r * 0.015, r * 0.015)
        for i, cell in enumerate(self._cells(body, r)):
            frac = (i + 0.5) / CELLS
            red = spec.in_red_zone(spec.minimum + frac * (spec.maximum - spec.minimum))
            p.setBrush(_alpha(HOT if red else CYAN, 30))
            p.drawRect(cell)

        draw_text(p, QPointF(c.x(), c.y() - r * 0.52), spec.label,
                  make_font(FONT, r * 0.12, QFont.Weight.DemiBold), TEXT_DIM)

    @staticmethod
    def _cells(body: QRectF, r: float) -> list[QRectF]:
        pad, gap = r * 0.045, r * 0.02
        inner = body.adjusted(pad, pad, -pad, -pad)
        w = (inner.width() - gap * (CELLS - 1)) / CELLS
        return [QRectF(inner.left() + i * (w + gap), inner.top(), w, inner.height())
                for i in range(CELLS)]

    def paint_fuel_foreground(self, p: QPainter, rect: QRectF, spec: MetricSpec,
                              state: GaugeState) -> None:
        s = square(rect)
        c, r = s.center(), s.width() / 2
        frac = spec.fraction(state.value)
        lit = max(1, math.ceil(frac * CELLS)) if frac > 0 else 0
        color = HOT if state.warning else CYAN

        p.setPen(Qt.PenStyle.NoPen)
        for cell in self._cells(self._battery_rect(s), r)[:lit]:
            p.setBrush(_alpha(color, 70))
            p.drawRect(cell.adjusted(-r * 0.012, -r * 0.012, r * 0.012, r * 0.012))
            p.setBrush(color)
            p.drawRect(cell)

        draw_text(p, QPointF(c.x(), c.y() - r * 0.21), f"{state.value:.0f}%",
                  make_font(FONT, r * 0.26, QFont.Weight.Light),
                  HOT if state.warning else TEXT)
        if state.detail:
            draw_text(p, QPointF(c.x(), c.y() + r * 0.52), state.detail,
                      make_font(FONT, r * 0.09), TEXT_DIM)
        self._warning_sign(p, QPointF(c.x(), c.y() + r * 0.74), r * 0.10, state.warning)
