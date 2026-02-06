# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BehavBox is a Raspberry Pi-based system for animal behavior training and experiments. It uses GPIO for hardware control (LEDs, pumps, sensors) and state machines for task logic.

## Development Setup

**On Raspberry Pi (production):**
```bash
conda env create -f environment/environment.yml
conda activate RPi_behavbox
```

**On macOS/desktop (mock development):**
```bash
pip install -e ./mock-gpiozero
```
This installs `mock_gpiozero`, which patches `sys.modules['gpiozero']` so all existing imports work unchanged. The directory uses a hyphen (`mock-gpiozero/`) to prevent Python namespace package shadowing.

## Running

**Run an experiment task:**
```bash
python3 task_protocol/headfixed_task/run_headfixed_task.py
```

**Run mock GPIO interactive test:**
```bash
python3 test_mock_gpio.py
```

Session info files must be configured per-day outside the repo (typically `~/experimental_data/<task>/session_info/session_info_YYYY-MM-DD.py`). The `manual_date` field is validated against the actual date at runtime.

## Architecture

### Core Layer (`essential/`)

**`BehavBox`** is the central hardware abstraction. It initializes all GPIO (LEDs, buttons/sensors, pumps, flipper, treadmill, ADC) and maintains a class-level `event_list` (deque) shared across instances.

**Event flow:** GPIO callback → appends event string to `BehavBox.event_list` → task's `run()` method poplefts and dispatches events based on current state.

**Sensor inversion (critical):**
- **Lick sensors** are inverted: `when_pressed` = animal *stops* licking (exit), `when_released` = animal *starts* licking (entry)
- **IR sensors** are normal: `when_pressed` = beam broken (entry), `when_released` = beam restored (exit)

### Task Layer (`task_protocol/`)

Each task subdirectory contains:
- `*_task.py` — state machine using `transitions` library with `@add_state_features(Timeout)`
- `*_task_information.py` — trial configuration with a card-deck draw system
- `run_*_task.py` — entry point script
- `session_info_*.py` — example session configuration (OrderedDict)

**State machine pattern:** States have `on_enter_*`, `on_exit_*`, and `on_timeout_*` handlers. Triggers are named transitions between states. The task's `run()` method is called in a tight loop, processing events from the shared deque.

### Mock GPIO (`mock-gpiozero/`)

All entry points use this bootstrap pattern:
```python
try:
    import mock_gpiozero
    mock_gpiozero.patch()
except ImportError:
    pass
```

`KeyboardSimulator` opens a tkinter window via `subprocess.Popen` (not threading/multiprocessing) because macOS requires tkinter on the main thread. Keys 1-3 simulate lick sensors, keys 4-6 simulate IR sensors.

### Key Dependencies

Runtime: `gpiozero`, `transitions`, `numpy`, `scipy`, `matplotlib`, `pygame`, `colorama`, `pysistence`
Hardware-specific (RPi only): `RPi.GPIO`, `smbus`, `picamera`

## Conventions

- `debug/` contains standalone calibration and test utilities, all with the mock_gpiozero bootstrap
- `obsolete/` is legacy code — do not modify
- Session info is an `OrderedDict` passed to all components (BehavBox, Task, Pump) as the single configuration object
- Pump calibration uses polynomial coefficients stored in session info
- Tasks save data as both `.mat` and `.pkl` files at session end
