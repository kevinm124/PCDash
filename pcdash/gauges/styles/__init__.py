"""Registry of available gauge styles. Add new styles to ``STYLES``."""

from .base import GaugeState, GaugeStyle
from .sporty import SportyStyle

STYLES: dict[str, type[GaugeStyle]] = {
    SportyStyle.key: SportyStyle,
}

DEFAULT_STYLE = SportyStyle.key


def create_style(key: str) -> GaugeStyle:
    return STYLES.get(key, STYLES[DEFAULT_STYLE])()


__all__ = ["GaugeState", "GaugeStyle", "STYLES", "DEFAULT_STYLE", "create_style"]
