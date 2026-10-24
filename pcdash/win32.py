"""Small Win32 helpers: click-through windows and system-wide hotkeys."""

from __future__ import annotations

import ctypes
import logging
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QTimer

log = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WM_HOTKEY = 0x0312

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
_MODIFIERS = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL, "alt": MOD_ALT,
              "shift": MOD_SHIFT, "win": MOD_WIN}
_NAMED_KEYS = {"space": 0x20, "pageup": 0x21, "pagedown": 0x22, "end": 0x23,
               "home": 0x24, "insert": 0x2D, "delete": 0x2E, "pause": 0x13,
               "scrolllock": 0x91}


# --- click-through ---------------------------------------------------------

def set_click_through(hwnd: int, enabled: bool) -> None:
    """Let mouse input pass through the window (WS_EX_TRANSPARENT).

    Changing the extended style in place avoids Qt re-creating the native
    window, which would happen with ``setWindowFlags``.
    """
    style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    if enabled:
        new = style | WS_EX_TRANSPARENT | WS_EX_LAYERED
    else:
        new = style & ~WS_EX_TRANSPARENT
    if new != style:
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new)


# --- global hotkeys --------------------------------------------------------

def parse_hotkey(text: str) -> tuple[int, int] | None:
    """Parse e.g. "Ctrl+Alt+F10" into (modifiers, virtual-key code)."""
    parts = [p.strip().lower() for p in text.split("+") if p.strip()]
    if not parts:
        return None
    *mods, key = parts
    modifiers = 0
    for mod in mods:
        if mod not in _MODIFIERS:
            return None
        modifiers |= _MODIFIERS[mod]
    if key in _NAMED_KEYS:
        vk = _NAMED_KEYS[key]
    elif key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    elif len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    else:
        return None
    return modifiers, vk


class GlobalHotkeys(QAbstractNativeEventFilter):
    """System-wide hotkeys via RegisterHotKey; callbacks run on the UI thread."""

    def __init__(self) -> None:
        super().__init__()
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._next_id = 1
        QCoreApplication.instance().installNativeEventFilter(self)

    def register(self, text: str, callback: Callable[[], None]) -> bool:
        parsed = parse_hotkey(text)
        if parsed is None:
            log.warning("Invalid hotkey %r", text)
            return False
        modifiers, vk = parsed
        hotkey_id = self._next_id
        self._next_id += 1
        # hwnd=None posts WM_HOTKEY to this thread's queue, so it keeps working
        # even if Qt re-creates the overlay's native window.
        if not user32.RegisterHotKey(None, hotkey_id, modifiers | MOD_NOREPEAT, vk):
            log.warning("Hotkey %s is already in use by another program", text)
            return False
        self._callbacks[hotkey_id] = callback
        return True

    def unregister_all(self) -> None:
        for hotkey_id in self._callbacks:
            user32.UnregisterHotKey(None, hotkey_id)
        self._callbacks.clear()

    def nativeEventFilter(self, event_type, message):  # noqa: N802 (Qt API)
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam in self._callbacks:
            QTimer.singleShot(0, self._callbacks[msg.wParam])
            return True, 0
        return False, 0
