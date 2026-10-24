# PCDash

A car-dashboard overlay for your Windows PC: live system stats drawn as
tachometers and dials, floating on your desktop in a transparent,
always-on-top window.

> **Status:** work in progress. Milestone 3 is done: three gauge styles,
> switchable at runtime.

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
- Frameless, transparent, always-on-top window
- Low overhead (about 0.2% total CPU): stats are read once a second on a
  background thread, needles animate only while moving, and each gauge's
  static face is cached as an image

Planned: click-through hotkey, tray icon, opacity/scale, layouts and saved
settings.

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

- **Left-drag** the gauge to move it.
- **Right-click** it for the menu (Style, Quit).

## Project layout

```
main.py                         entry point
pcdash/
  app.py                        wires the data provider to the window
  overlay.py                    frameless transparent always-on-top window
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
