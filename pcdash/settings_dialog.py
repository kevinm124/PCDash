"""Settings window. Every change applies immediately and is saved."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QSlider, QVBoxLayout,
                               QWidget)

from .config import CONFIG_PATH, LAYOUTS, OPACITY_RANGE, SCALE_RANGE
from .gauges.styles import STYLES

if TYPE_CHECKING:
    from .controller import Controller


class SettingsDialog(QDialog):
    def __init__(self, controller: Controller) -> None:
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("PCDash settings")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._ctl = controller
        s = controller.settings

        form = QFormLayout()

        self._style = QComboBox()
        for key, cls in STYLES.items():
            self._style.addItem(cls.name, key)
        self._style.setCurrentIndex(max(0, self._style.findData(s.style)))
        self._style.currentIndexChanged.connect(
            lambda: controller.set_style(self._style.currentData()))
        form.addRow("Style", self._style)

        self._layout = QComboBox()
        for key, name in LAYOUTS.items():
            self._layout.addItem(name, key)
        self._layout.setCurrentIndex(max(0, self._layout.findData(s.layout)))
        self._layout.currentIndexChanged.connect(
            lambda: controller.set_layout(self._layout.currentData()))
        form.addRow("Layout", self._layout)

        self._main = QComboBox()
        for spec in controller.specs:
            self._main.addItem(spec.label, spec.key)
        self._main.setCurrentIndex(max(0, self._main.findData(s.main_gauge)))
        self._main.currentIndexChanged.connect(
            lambda: controller.set_main_gauge(self._main.currentData()))
        form.addRow("Main gauge", self._main)

        form.addRow("Opacity", self._slider(
            OPACITY_RANGE, s.opacity, controller.set_opacity))
        form.addRow("Size", self._slider(
            SCALE_RANGE, s.scale, controller.set_scale))

        gauges = QGroupBox("Visible gauges")
        gauge_box = QHBoxLayout(gauges)
        for spec in controller.specs:
            box = QCheckBox(spec.label)
            box.setChecked(spec.key not in s.hidden)
            box.toggled.connect(lambda on, k=spec.key, b=box: self._toggle_gauge(k, on, b))
            gauge_box.addWidget(box)
        gauge_box.addStretch(1)

        hints = QLabel(
            f"<b>{s.hotkey_click_through}</b> toggles click-through, "
            f"<b>{s.hotkey_show_hide}</b> shows/hides the overlay.<br>"
            "On the overlay: drag to move, Ctrl+wheel to resize, "
            "Shift+wheel for opacity, right-click for the menu.<br>"
            f"Advanced options and hotkeys: <code>{CONFIG_PATH}</code>")
        hints.setWordWrap(True)
        hints.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(gauges)
        root.addWidget(hints)
        root.addWidget(buttons)
        self.resize(460, self.sizeHint().height())

    @staticmethod
    def _slider(value_range: tuple[float, float], value: float, apply) -> QWidget:
        """Percent slider for a float setting, with a live value label."""
        low, high = (round(v * 100) for v in value_range)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(round(value * 100))
        label = QLabel(f"{slider.value()}%")
        label.setMinimumWidth(40)

        def changed(v: int) -> None:
            label.setText(f"{v}%")
            apply(v / 100)

        slider.valueChanged.connect(changed)
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(slider)
        box.addWidget(label)
        return row

    def _toggle_gauge(self, key: str, on: bool, box: QCheckBox) -> None:
        if not self._ctl.set_gauge_visible(key, on):
            box.blockSignals(True)          # refused: keep at least one gauge
            box.setChecked(True)
            box.blockSignals(False)
