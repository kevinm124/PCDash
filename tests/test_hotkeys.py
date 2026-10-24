import pytest

from pcdash.win32 import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, parse_hotkey


@pytest.mark.parametrize("text, expected", [
    ("Ctrl+Alt+F10", (MOD_CONTROL | MOD_ALT, 0x79)),
    ("shift + win + p", (MOD_SHIFT | MOD_WIN, ord("P"))),
    ("Ctrl+5", (MOD_CONTROL, ord("5"))),
    ("Alt+PageUp", (MOD_ALT, 0x21)),
    ("F24", (0, 0x87)),
])
def test_valid(text, expected):
    assert parse_hotkey(text) == expected


@pytest.mark.parametrize("text", ["", "Ctrl+", "Hyper+A", "Ctrl+F25", "Ctrl+Banana"])
def test_invalid(text):
    assert parse_hotkey(text) is None
