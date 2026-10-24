import json

from pcdash.config import Settings


def test_missing_file_gives_defaults(tmp_path):
    assert Settings.load(tmp_path / "nope.json") == Settings()


def test_corrupt_file_gives_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")
    assert Settings.load(path) == Settings()


def test_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    s = Settings(style="retro", layout="grid", hidden=["vram"], opacity=0.6,
                 scale=1.5, x=10, y=-20, click_through=True)
    s.save(path)
    assert Settings.load(path) == s


def test_invalid_values_are_ignored_and_clamped(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "poll_ms": "fast",        # wrong type -> default
        "visible": 1,             # int is not bool -> default
        "opacity": 5,             # clamped
        "scale": 0.01,            # clamped
        "layout": "spiral",       # unknown -> dashboard
        "hidden": ["a", "a", 3],  # non-string -> default
        "unknown_key": True,      # ignored
    }), encoding="utf-8")
    s = Settings.load(path)
    assert s.poll_ms == 1000
    assert s.visible is True
    assert s.opacity == 1.0
    assert s.scale == 0.4
    assert s.layout == "dashboard"
    assert s.hidden == []
