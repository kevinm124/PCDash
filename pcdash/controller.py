"""Ties settings, overlay, tray icon, hotkeys and the stats poller together."""

from __future__ import annotations

import logging

from PySide6.QtCore import QCoreApplication, QObject, QPoint, QTimer
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import __version__, autostart
from .config import LAYOUTS, OPACITY_RANGE, SCALE_RANGE, Settings
from .gauges.styles import STYLES
from .icon import app_icon
from .overlay import OverlayWindow
from .providers import DataProvider, Reading
from .providers.base import FUEL
from .settings_dialog import SettingsDialog
from .stats_poller import StatsPoller
from .win32 import GlobalHotkeys

log = logging.getLogger(__name__)

SAVE_DELAY_MS = 800


def _clamp(value: float, bounds: tuple[float, float]) -> float:
    return min(max(value, bounds[0]), bounds[1])


class Controller(QObject):
    def __init__(self, settings: Settings, provider: DataProvider) -> None:
        super().__init__()
        self.settings = settings
        self.provider = provider
        self.specs = provider.metrics()
        self._dialog: SettingsDialog | None = None
        self._shut_down = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self.settings.save)

        # Overlay.
        if settings.style not in STYLES:
            settings.style = next(iter(STYLES))
        self.overlay = OverlayWindow(self.specs, settings.style)
        self.overlay.setWindowIcon(app_icon())
        self._rebuild()
        self.overlay.set_scale(settings.scale)
        self.overlay.setWindowOpacity(settings.opacity)
        self._place_window()
        self.overlay.set_click_through(settings.click_through)
        self.overlay.moved.connect(self._on_moved)
        self.overlay.menu_requested.connect(lambda pos: self.menu.popup(pos))
        self.overlay.scale_step.connect(lambda d: self.set_scale(self.settings.scale + 0.1 * d))
        self.overlay.opacity_step.connect(
            lambda d: self.set_opacity(self.settings.opacity + 0.05 * d))
        self.overlay.close_requested.connect(lambda: self.set_visible(False))

        # Live data.
        self.poller = StatsPoller(provider, settings.poll_ms, self)
        self.poller.readings.connect(self.overlay.apply_readings)
        self.poller.readings.connect(self._update_tooltip)
        self.poller.start()

        # Tray icon + shared menu (also shown on right-click of the overlay).
        self.menu = QMenu()
        self._build_menu()
        self.menu.aboutToShow.connect(self._refresh_menu)
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(f"PCDash {__version__}")
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # Global hotkeys.
        self.hotkeys = GlobalHotkeys()
        failed = [text for text, action in (
            (settings.hotkey_click_through, self.toggle_click_through),
            (settings.hotkey_show_hide, self.toggle_visible),
        ) if not self.hotkeys.register(text, action)]
        if failed:
            self._notify("Hotkey unavailable: " + ", ".join(failed)
                         + ". Change it in the config file.")

        if settings.visible:
            self.overlay.show()
        else:
            self._notify("PCDash is running in the system tray.")
        if settings.click_through:
            self._notify_click_through()

        app = QGuiApplication.instance()
        app.aboutToQuit.connect(self.shutdown)
        # Unplugging a monitor can leave the overlay off-screen: bring it back.
        app.screenRemoved.connect(lambda _: QTimer.singleShot(500, self._ensure_on_screen))

    # --- helpers -----------------------------------------------------------

    def _visible_keys(self) -> list[str]:
        return [s.key for s in self.specs if s.key not in self.settings.hidden]

    def _rebuild(self) -> None:
        self.overlay.set_layout(self.settings.layout, self._visible_keys(),
                                self.settings.main_gauge)

    def _save_later(self) -> None:
        self._save_timer.start()

    def _notify(self, text: str) -> None:
        if hasattr(self, "tray") and self.tray.isVisible():
            self.tray.showMessage("PCDash", text, app_icon(), 4000)
        log.info(text)

    def _notify_click_through(self) -> None:
        self._notify(f"Click-through is ON - the overlay ignores the mouse. "
                     f"Press {self.settings.hotkey_click_through} to turn it off.")

    def _place_window(self) -> None:
        s = self.settings
        if s.x is not None and s.y is not None:
            if QGuiApplication.screenAt(QPoint(s.x + 20, s.y + 20)) is not None:
                self.overlay.move(s.x, s.y)
                return
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.overlay.move(area.right() - self.overlay.width() - 20, area.top() + 20)

    def _ensure_on_screen(self) -> None:
        pos = self.overlay.pos()
        if QGuiApplication.screenAt(QPoint(pos.x() + 20, pos.y() + 20)) is None:
            self.settings.x = self.settings.y = None
            self._place_window()

    def _update_tooltip(self, readings: dict[str, Reading]) -> None:
        parts = [f"{spec.label} {readings[spec.key].value:.0f}%"
                 for spec in self.specs if spec.kind != FUEL and spec.key in readings]
        self.tray.setToolTip(f"PCDash - {', '.join(parts)}"[:127])

    def _on_moved(self, pos: QPoint) -> None:
        self.settings.x, self.settings.y = pos.x(), pos.y()
        self._save_later()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    # --- actions -----------------------------------------------------------

    def set_visible(self, visible: bool) -> None:
        self.settings.visible = visible
        if visible:
            self.overlay.show()
            self.overlay.raise_()
        else:
            self.overlay.hide()
        self._save_later()

    def toggle_visible(self) -> None:
        self.set_visible(not self.overlay.isVisible())

    def set_click_through(self, enabled: bool) -> None:
        self.settings.click_through = enabled
        self.overlay.set_click_through(enabled)
        if enabled:
            self._notify_click_through()
        self._save_later()

    def toggle_click_through(self) -> None:
        self.set_click_through(not self.settings.click_through)

    def set_style(self, key: str) -> None:
        if key in STYLES:
            self.settings.style = key
            self.overlay.set_style(key)
            self._save_later()

    def set_layout(self, layout: str) -> None:
        if layout in LAYOUTS:
            self.settings.layout = layout
            self._rebuild()
            self._save_later()

    def set_main_gauge(self, key: str) -> None:
        self.settings.main_gauge = key
        self._rebuild()
        self._save_later()

    def set_gauge_visible(self, key: str, visible: bool) -> bool:
        """Show/hide one gauge. Refuses to hide the last visible gauge."""
        hidden = self.settings.hidden
        if visible and key in hidden:
            hidden.remove(key)
        elif not visible and key not in hidden:
            if len(self._visible_keys()) <= 1:
                return False
            hidden.append(key)
        self._rebuild()
        self._save_later()
        return True

    def set_opacity(self, opacity: float) -> None:
        self.settings.opacity = round(_clamp(opacity, OPACITY_RANGE), 2)
        self.overlay.setWindowOpacity(self.settings.opacity)
        self._save_later()

    def set_scale(self, scale: float) -> None:
        self.settings.scale = round(_clamp(scale, SCALE_RANGE), 2)
        self.overlay.set_scale(self.settings.scale)
        self._save_later()

    def set_autostart(self, enabled: bool) -> None:
        if not autostart.set_enabled(enabled):
            self._notify("Could not change the Windows startup setting.")

    def open_settings(self) -> None:
        if self._dialog is None:
            self._dialog = SettingsDialog(self)
            self._dialog.destroyed.connect(lambda: setattr(self, "_dialog", None))
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()

    def quit(self) -> None:
        self.shutdown()
        QCoreApplication.exit(0)

    def shutdown(self) -> None:
        if self._shut_down:
            return
        self._shut_down = True
        self._save_timer.stop()
        self.settings.save()
        self.hotkeys.unregister_all()
        self.poller.stop()
        self.tray.hide()
        if self._dialog is not None:
            self._dialog.close()
        self.overlay.allow_close()
        self.overlay.close()
        self.provider.close()

    # --- menu --------------------------------------------------------------

    def _build_menu(self) -> None:
        m = self.menu
        self._act_show = m.addAction("Hide overlay", self.toggle_visible)
        self._act_click = m.addAction(
            f"Click-through\t{self.settings.hotkey_click_through}")
        self._act_click.setCheckable(True)
        self._act_click.triggered.connect(self.set_click_through)
        m.addSeparator()

        self._style_actions = self._radio_menu(
            m.addMenu("Style"), {k: c.name for k, c in STYLES.items()}, self.set_style)
        self._layout_actions = self._radio_menu(
            m.addMenu("Layout"), LAYOUTS, self.set_layout)
        self._main_actions = self._radio_menu(
            m.addMenu("Main gauge"), {s.key: s.label for s in self.specs},
            self.set_main_gauge)

        gauges = m.addMenu("Gauges")
        self._gauge_actions: dict[str, QAction] = {}
        for spec in self.specs:
            action = gauges.addAction(spec.label)
            action.setCheckable(True)
            action.triggered.connect(
                lambda on, k=spec.key: self.set_gauge_visible(k, on))
            self._gauge_actions[spec.key] = action

        m.addSeparator()
        self._act_autostart = m.addAction("Start with Windows")
        self._act_autostart.setCheckable(True)
        self._act_autostart.triggered.connect(self.set_autostart)
        m.addAction("Settings…", self.open_settings)
        m.addSeparator()
        m.addAction("Quit PCDash", self.quit)

    @staticmethod
    def _radio_menu(menu: QMenu, items: dict[str, str], apply) -> dict[str, QAction]:
        group = QActionGroup(menu)
        actions = {}
        for key, name in items.items():
            action = menu.addAction(name)
            action.setCheckable(True)
            action.triggered.connect(lambda _=False, k=key: apply(k))
            group.addAction(action)
            actions[key] = action
        return actions

    def _refresh_menu(self) -> None:
        s = self.settings
        self._act_show.setText("Hide overlay" if self.overlay.isVisible() else "Show overlay")
        self._act_click.setChecked(s.click_through)
        self._act_autostart.setChecked(autostart.is_enabled())
        for actions, current in ((self._style_actions, s.style),
                                 (self._layout_actions, s.layout),
                                 (self._main_actions, s.main_gauge)):
            for key, action in actions.items():
                action.setChecked(key == current)
        visible = self._visible_keys()
        for key, action in self._gauge_actions.items():
            action.setChecked(key in visible)
            # Don't allow unticking the last visible gauge.
            action.setEnabled(not (len(visible) == 1 and key in visible))
