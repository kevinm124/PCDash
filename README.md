# PCDash

A car-dashboard overlay for your Windows PC: live system stats drawn as
tachometers and dials, floating on your desktop in a transparent,
always-on-top window.

> **Status:** work in progress. Milestone 4 is done: tray icon, click-through
> hotkey, layouts, opacity/size and saved settings.

## Features

- **CPU** usage as the big main tachometer, with a redline zone near 100%
- **RAM** usage (% plus GB used / total)
- **GPU** usage and **VRAM** (plus GPU temperature on NVIDIA cards)
  - NVIDIA: read via NVML (`nvidia-ml-py`)
  - AMD / Intel: read from Windows performance counters, the same source
    Task Manager uses
- **Disk free space** per fixed drive (C:, D:, …) as fuel gauges, E to F
- Three styles, switchable while running (right-click → Style):
  - **Sporty**: dark face, red needle and redline, sharp DIN-style numbers
  - **Retro**: cream face, black serif numbers, chrome bezel, thin needle,
    amber jewel warning lamps
  - **Futuristic**: EV-style digital cluster with glowing segmented neon arcs,
    big digital numbers, no needle; drives shown as battery bars
- Needles that ease smoothly toward each new value instead of jumping
- Warning lamps: CPU ≥ 90%, RAM ≥ 85%, GPU ≥ 95%, VRAM ≥ 90%, drive ≤ 10% free
- Frameless, transparent, always-on-top window you can drag anywhere
- **Click-through** mode so clicks go to whatever is underneath, toggled with
  a global hotkey
- Adjustable **opacity** and **size**
- Four **layouts**: Dashboard (big main gauge + small ones), Row, Grid,
  Single gauge; pick which gauges are shown and which one is the main gauge
- **System tray** icon with the full menu
- Settings (position, size, style, layout, …) remembered between launches
- Low overhead (about 0.2% total CPU): stats are read once a second on a
  background thread, needles animate only while moving, and each gauge's
  static face is cached as an image

## Requirements

- Windows 10/11
- Python 3.13

## Install

```bash
git clone <your-repo-url> PCDash
cd PCDash
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```bash
.venv\Scripts\python.exe main.py
```

PCDash runs in the system tray (bottom-right, maybe under the ^ arrow).
**Left-click** the tray icon to show/hide the overlay; **right-click** it for
the menu.

### Controls

| Action | How |
| --- | --- |
| Move the overlay | Left-drag it |
| Menu | Right-click the overlay or the tray icon |
| Resize | Ctrl + mouse wheel over the overlay, or Settings → Size |
| Opacity | Shift + mouse wheel over the overlay, or Settings → Opacity |
| Click-through on/off | **Ctrl+Alt+F10** (anywhere) or menu → Click-through |
| Show/hide overlay | **Ctrl+Alt+F11** (anywhere) or left-click the tray icon |
| Style, layout, gauges | Menu → Style / Layout / Main gauge / Gauges |
| Quit | Menu → Quit PCDash |

While click-through is on, the overlay ignores the mouse completely. Use the
hotkey or the tray menu to turn it off again.

### Settings file

Settings are saved automatically to `%APPDATA%\PCDash\config.json`. Most
options are in the Settings window; a few advanced ones are only in the file
(quit PCDash before editing it):

| Key | Default | Meaning |
| --- | --- | --- |
| `hotkey_click_through` | `"Ctrl+Alt+F10"` | Modifiers `Ctrl`, `Alt`, `Shift`, `Win` + a key (`A`–`Z`, `0`–`9`, `F1`–`F24`, `Home`, `PageUp`, …) |
| `hotkey_show_hide` | `"Ctrl+Alt+F11"` | Same format |
| `poll_ms` | `1000` | How often stats are read (250–10000 ms) |
| `animation_fps` | `30` | Needle frame rate while moving (10–144) |
| `gpu_backend` | `"auto"` | `"auto"`, `"nvml"` (NVIDIA) or `"pdh"` (Windows counters) |

Delete the file to reset everything to defaults.

## Project layout

```
main.py                         entry point
pcdash/
  app.py                        startup: settings, single-instance lock
  controller.py                 ties overlay, tray, hotkeys and settings together
  overlay.py                    frameless transparent always-on-top window + layouts
  settings_dialog.py            Settings window
  config.py                     Settings dataclass, JSON load/save
  win32.py                      click-through and global hotkeys (Win32 API)
  icon.py                       tray/app icon drawn in code
  stats_poller.py               polls the provider on a background thread
  providers/
    base.py                     DataProvider interface (MetricSpec, Reading)
    pc_stats.py                 CPU / RAM / GPU / disk stats
    gpu.py                      GPU backends: NVML and Windows perf counters
  gauges/
    gauge_widget.py             needle smoothing + cached static layer
    styles/
      base.py                   GaugeStyle interface + geometry helpers
      sporty.py                 Sporty style (dial + fuel gauge)
      retro.py                  Retro style
      futuristic.py             Futuristic style
```

### Adding a style

1. Create `pcdash/gauges/styles/mystyle.py` with a `GaugeStyle` subclass that
   sets `key` and `name` and implements `paint_dial_background`,
   `paint_dial_foreground`, `paint_fuel_background` and `paint_fuel_foreground`.
   Background methods draw the static parts (they are cached); foreground
   methods draw the needle/value every frame.
2. Add the class to `STYLES` in `pcdash/gauges/styles/__init__.py`.

It then shows up in the Style menu automatically.

Data sources and drawing are kept separate: a `DataProvider` only reports
numbers (`MetricSpec` + `Reading`), and a `GaugeStyle` only draws them, so
new stats or new styles can be added without touching the other side.

## License

[MIT](LICENSE)
