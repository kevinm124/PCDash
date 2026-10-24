"""Registry of available gauge styles. Add new styles to ``STYLES``."""

from .base import GaugeState, GaugeStyle
from .futuristic import FuturisticStyle
from .retro import RetroStyle
from .sporty import SportyStyle

STYLES: dict[str, type[GaugeStyle]] = {
    cls.key: cls for cls in (SportyStyle, RetroStyle, FuturisticStyle)
}

DEFAULT_STYLE = SportyStyle.key


def create_style(key: str) -> GaugeStyle:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])()


__all__ = ["GaugeState", "GaugeStyle", "STYLES", "DEFAULT_STYLE", "create_style"]
