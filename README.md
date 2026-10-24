# PCDash

A car-dashboard overlay for your Windows PC: live system stats drawn as
tachometers and dials, floating on your desktop in a transparent,
always-on-top window.

> **Status:** work in progress. Milestone 1 is done: one CPU tachometer in an
> always-on-top transparent window.

## Features

- CPU usage as the main tachometer, with a redline zone near 100%
- Needles that ease smoothly toward each new value instead of jumping
- Warning lamp that lights up when a value enters the danger zone
- Frameless, transparent, always-on-top window
- Low overhead: stats are polled once a second, the needle animates only while
  it moves, and each gauge's static face is cached as an image

Planned: RAM, GPU/VRAM and disk gauges, three switchable styles (Sporty,
Retro, Futuristic), click-through hotkey, tray icon and saved settings.

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
- **Right-click** it for the menu (Quit).

## Project layout

```
main.py                         entry point
pcdash/
  app.py                        wires the data provider to the window
  overlay.py                    frameless transparent always-on-top window
  providers/
    base.py                     DataProvider interface (MetricSpec, Reading)
    pc_stats.py                 PC stats via psutil
  gauges/
    gauge_widget.py             needle smoothing + cached static layer
    styles/
      base.py                   GaugeStyle interface + geometry helpers
      sporty.py                 Sporty style
```

Data sources and drawing are kept separate: a `DataProvider` only reports
numbers (`MetricSpec` + `Reading`), and a `GaugeStyle` only draws them, so
new stats or new styles can be added without touching the other side.

## License

[MIT](LICENSE)
