"""User settings, stored as JSON in %APPDATA%\\PCDash\\config.json.

Unknown keys are ignored and invalid values fall back to defaults, so a
hand-edited or outdated config file never stops the app from starting.
Set the ``PCDASH_CONFIG`` environment variable to use a different file.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

log = logging.getLogger(__name__)

APP_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "PCDash"
CONFIG_PATH = Path(os.environ.get("PCDASH_CONFIG") or APP_DIR / "config.json")

LAYOUTS = {
    "dashboard": "Dashboard",
    "row": "Row",
    "grid": "Grid",
    "single": "Single gauge",
}

OPACITY_RANGE = (0.2, 1.0)
SCALE_RANGE = (0.4, 2.5)


@dataclass
class Settings:
    style: str = "sporty"
    layout: str = "dashboard"
    main_gauge: str = "cpu"           # big gauge in "dashboard" and "single"
    hidden: list[str] = field(default_factory=list)   # metric keys not shown
    opacity: float = 1.0
    scale: float = 1.0
    x: int | None = None              # window position; None = default corner
    y: int | None = None
    visible: bool = True
    click_through: bool = False
    hotkey_click_through: str = "Ctrl+Alt+F10"
    hotkey_show_hide: str = "Ctrl+Alt+F11"
    poll_ms: int = 1000               # how often stats are read
    animation_fps: int = 30           # needle frame rate while moving
    gpu_backend: str = "auto"         # "auto", "nvml" or "pdh"

    # --- persistence -------------------------------------------------------

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> Settings:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        except (OSError, ValueError) as exc:
            log.warning("Could not read %s (%s); using defaults", path, exc)
            return cls()
        if not isinstance(data, dict):
            return cls()

        settings = cls()
        defaults = cls()
        for f in fields(cls):
            if f.name not in data:
                continue
            value, default = data[f.name], getattr(defaults, f.name)
            if f.name in ("x", "y"):
                ok = value is None or (isinstance(value, int) and not isinstance(value, bool))
            elif isinstance(default, bool):
                ok = isinstance(value, bool)
            elif isinstance(default, float):
                ok = isinstance(value, (int, float)) and not isinstance(value, bool)
                value = float(value) if ok else value
            elif isinstance(default, int):
                ok = isinstance(value, int) and not isinstance(value, bool)
            elif isinstance(default, list):
                ok = isinstance(value, list) and all(isinstance(v, str) for v in value)
            else:
                ok = isinstance(value, str)
            if ok:
                setattr(settings, f.name, value)
            else:
                log.warning("Ignoring invalid config value %s=%r", f.name, value)
        settings.normalize()
        return settings

    def save(self, path: Path = CONFIG_PATH) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
            os.replace(tmp, path)       # atomic: never leaves a half-written file
        except OSError as exc:
            log.warning("Could not save settings to %s: %s", path, exc)

    # --- validation --------------------------------------------------------

    def normalize(self) -> None:
        """Clamp values into their allowed ranges."""
        if self.layout not in LAYOUTS:
            self.layout = "dashboard"
        self.opacity = min(max(self.opacity, OPACITY_RANGE[0]), OPACITY_RANGE[1])
        self.scale = min(max(self.scale, SCALE_RANGE[0]), SCALE_RANGE[1])
        self.poll_ms = min(max(self.poll_ms, 250), 10_000)
        self.animation_fps = min(max(self.animation_fps, 10), 144)
        if self.gpu_backend not in ("auto", "nvml", "pdh"):
            self.gpu_backend = "auto"
        self.hidden = list(dict.fromkeys(self.hidden))
