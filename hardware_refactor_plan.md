# BehavBox Hardware Library Refactor

*Branch analysis and unification plan -- prepared February 2026 for the Sjulson Lab*

## Contents

1. [Overview & Motivation](#1-overview--motivation)
2. [Branch-by-Branch Analysis](#2-branch-by-branch-analysis)
3. [GPIO Pin Conflicts Across Branches](#3-gpio-pin-conflicts-across-branches)
4. [Pump Hardware Configurations](#4-pump-hardware-configurations)
5. [Architectural Patterns](#5-architectural-patterns)
6. [Head-Fixed vs. Freely-Moving](#6-head-fixed-vs-freely-moving-do-we-need-two-configurations)
7. [Unification Plan](#7-unification-plan)
8. [Platform Auto-Detection](#8-platform-auto-detection)
9. [Migration Path](#9-migration-path)

---

## 1. Overview & Motivation

The `essential/` directory in **RPi4_behavior_boxes** contains the hardware interface layer: `behavbox.py`, `FlipperOutput.py`, `Treadmill.py`, `ADS1x15.py`, and `visualstim.py`. This code was intended to be written once and shared by all users, but because task code lives in the same repository, users created per-person branches and began modifying the hardware layer to suit their specific experimental configurations.

The result: **at least 6 distinct, incompatible versions** of the hardware interface code across the repository's branches. The goal of this refactor is to:

1. Audit every branch's hardware changes
2. Unify them into a single, configurable hardware library in a **new dedicated repository**
3. Support both head-fixed and freely-moving configurations
4. Auto-detect RPi vs. desktop platforms (macOS, Linux x86-64, WSL) and use real or mock GPIO accordingly

---

## 2. Branch-by-Branch Analysis

17 remote branches were examined. They fall into four categories:

| Category | Branches | Hardware Changes |
|----------|----------|-----------------|
| **Major changes** | matt-behavior, headfixed_soyounk, mitchfarrell-context, benville_gonogo | Significant modifications to pins, classes, or architecture |
| **Minor changes** | treadmill_only, context, context_vis | Small pin reassignments or pump calibration tweaks |
| **No changes** | charlie-irig, juliabenville_CueIVSA, rbb-lab, devEFO | Identical to main |
| **Deleted essential/** | go_nogo, go_nogo_temp_branch | Hardware code removed entirely (task-only branches) |

### `origin/matt-behavior` -- Matthew Chin [Major] [Head-fixed]

**Last updated:** 2026-02-04 | **The most extensively modified branch.**

**Architectural changes:**

- **New file: `base_classes.py`** -- abstract base classes (`Box`, `PumpBase`, `Presenter`, `Model`, `GUI`, `VisualStimBase`) defining the interface contract for the whole system
- **New file: `gui.py`** -- extracted `PygameGUI` class (plotting/display separated from BehavBox)
- **New file: `pyqtgui.py`** -- alternative PyQt-based GUI
- **New file: `dummy_box.py`** -- software mock of BehavBox for off-Pi testing
- **New file: `visualstim_concurrent.py`** -- multiprocess grating system with Queue-based commands
- **BehavBox now inherits from `Box`** (abstract base class) instead of `object`
- **Callbacks extracted from BehavBox** into a `Presenter` class via `set_callbacks(presenter)` -- all IR and lick callbacks are wired to the presenter, not hardcoded in BehavBox
- **GUI removed from BehavBox** -- no more `check_keybd()` or `check_plot()` in the hardware layer
- **Lick debouncing** added in `Model` base class with configurable `lick_min_time`/`lick_max_time`

**Hardware changes:**

- **Lick callback inversion REVERSED:** `when_pressed = left_entry` (opposite of main). Comment: *"This makes more sense intuitively??"*
- **Configurable lick polarity:** new `session_info["lick_input_setting"]` with `"signal_low"` / `"signal_high"` options
- **cueLED4 changed:** GPIO 14 from `PWMLED` to plain `LED`, aliased as `sound3`
- **DIO5 (GPIO 11) commented out**
- **Ephys rig support:** new `session_info['ephys_rig']` flag with dedicated video IP and picamera2 scripts

**FlipperOutput changes:**

- Base class changed from `DigitalOutputDevice` to `LED`
- **Barcode system:** encodes a random 32-bit integer as a serial bit pattern for temporal alignment with ephys data
- Better thread management with shared `Event()` flag
- Flipper idles in ON state (high) instead of OFF

**Pump changes:**

- Inherits from `PumpBase(ABC)`
- New `blink()` and `toggle()` methods for calibration
- Calibration coefficients cached at init

### `origin/headfixed_soyounk` -- Soyoun Kim [Minor] [Head-fixed]

**Last updated:** 2024-03-15

- **lick3 (GPIO 15) disabled** and repurposed as `sound3 = LED(15)`
- **sound4 added** on GPIO 9 (was DIO3, previously commented out)
- Needs 4 sound triggers for head-fixed auditory experiments, doesn't need center lick

### `origin/mitchfarrell-context`, `context_vis`, `context` -- Mitch Farrell [Major] [Freely-moving]

**Last updated:** 2024-09-13 (mitchfarrell-context), 2023-09-18 / 2023-04-26 (others)

- **All IR sensors removed** -- freely-moving context task uses lick sensors only
- **reserved_rx1 (GPIO 13) and reserved_rx2 (GPIO 16) added** as extra button inputs (repurposed from IR_rx4/rx5)
- **cueLED3 (GPIO 17), DIO4 (GPIO 10), DIO5 (GPIO 11) commented out**
- **Pump uses hardcoded `tube_fit = 0.13 ml/s`** calibration instead of polynomial coefficients, and takes no `session_info` argument
- **Directory structure changed:** `essential/` deleted; files moved to repo root

### `origin/benville_gonogo`, `ssrt_task`, `visualstim`, `context_video_stim` -- Duy Tran / Season [Major] [Freely-moving]

**Last updated:** 2024-05-30 (benville_gonogo), 2022-01-10 (ssrt_task)

- **No lick sensors at all** -- GPIO 26, 27, 15 repurposed as `sound1`, `sound2`, `sound3`
- **5 total sound outputs** (GPIO 26, 27, 15, 23, 24)
- **IR callbacks use semantic names:** `left_IR_entry` / `right_IR_entry` instead of `IR_1_entry` / `IR_2_entry`
- **Syringe pump stepper motors** instead of solenoid valves -- completely different Pump class that calculates stepper steps from syringe diameter (12.06mm for 5mL syringe)
- **pump4 on GPIO 8** (not 7), **pump5 on GPIO 7**, **pump_en on GPIO 25** (enable pin for stepper)
- Smaller pygame window (200x200)

### `origin/treadmill_only` -- Season (Tian Qiu) [Minor] [Head-fixed]

**Last updated:** 2023-04-27

- **DIO4 (GPIO 10) -> reserved_rx1 (Button)**, **DIO5 (GPIO 11) -> reserved_rx2 (Button)**
- Otherwise identical to main (has both IR sensors and lick sensors active)

### Branches with **no hardware changes** [Identical to main]

`charlie-irig` (Charlie, 2025-07-30), `juliabenville_CueIVSA` (Julia Benville, 2025-05-29), `rbb-lab` (Eliezyer, 2025-01-08), `devEFO` (Eliezyer, 2023-06-02)

---

## 3. GPIO Pin Conflicts Across Branches

The following table highlights pins whose usage **differs** across branches. Cells marked with `**` indicate a conflict with the main branch assignment.

| GPIO | main | matt-behavior | soyounk | mitchfarrell | benville/ssrt | treadmill_only |
|------|------|---------------|---------|--------------|---------------|----------------|
| **7** | pump4 | pump4 | pump4 | pump4 | **pump5** | pump4 |
| **8** | pump_air | pump_air | pump_air | pump_air | **pump4** | pump_air |
| **9** | *commented* | *commented* | **sound4 (LED)** | *commented* | *commented* | *commented* |
| **10** | DIO4 (LED) | DIO4 (LED) | DIO4 (LED) | *commented* | DIO4 (LED) | **reserved_rx1 (Button)** |
| **11** | DIO5 (LED) | *commented* | DIO5 (LED) | *commented* | DIO5 (LED) | **reserved_rx2 (Button)** |
| **13** | IR_rx4 (Button) | IR_rx4 (Button) | IR_rx4 (Button) | **reserved_rx1 (Button)** | IR_rx4 (Button) | IR_rx4 (Button) |
| **14** | cueLED4 (PWMLED) | **cueLED4 (LED) + sound3** | cueLED4 (PWMLED) | cueLED4 (PWMLED) | cueLED4 (PWMLED) | cueLED4 (PWMLED) |
| **15** | lick3 (Button) | lick3 (Button) | **sound3 (LED)** | lick3 (Button) | **sound3 (LED)** | lick3 (Button) |
| **16** | IR_rx5 (Button) | IR_rx5 (Button) | IR_rx5 (Button) | **reserved_rx2 (Button)** | IR_rx5 (Button) | IR_rx5 (Button) |
| **17** | cueLED3 (PWMLED) | cueLED3 (PWMLED) | cueLED3 (PWMLED) | ***commented*** | cueLED3 (PWMLED) | cueLED3 (PWMLED) |
| **25** | pump_vacuum | pump_vacuum | pump_vacuum | pump_vacuum | **pump_en (stepper enable)** | pump_vacuum |
| **26** | lick1 (Button) | lick1 (Button) | lick1 (Button) | lick1 (Button) | **sound1 (LED)** | lick1 (Button) |
| **27** | lick2 (Button) | lick2 (Button) | lick2 (Button) | lick2 (Button) | **sound2 (LED)** | lick2 (Button) |

> **Key takeaway:** The pin conflicts are not random -- they reflect **two fundamentally different hardware configurations** (head-fixed vs. freely-moving) that need different sets of sensors and actuators on the same physical GPIO header.

---

## 4. Pump Hardware Configurations

| Branches | Pump Type | Calibration Method | Pump Pins |
|----------|-----------|-------------------|-----------|
| main, matt-behavior, headfixed_soyounk, treadmill_only | Solenoid valves | Linear coefficients from `session_info`: `slope * (reward_size/1000) + intercept` | 19, 20, 21, 7, 8 (air), 25 (vacuum) |
| mitchfarrell-context, context_vis, context | Solenoid valves | Hardcoded `tube_fit = 0.13 ml/s`: `duration = (reward_size/1000) / tube_fit` | Same as above |
| benville_gonogo, ssrt_task, visualstim, context_video_stim | **Syringe pump stepper motors** | Calculated from syringe diameter (12.06mm for 5mL) | 19, 20, 21, **8**, **7** (pump5), **25** (enable) |

---

## 5. Architectural Patterns

| Feature | main | matt-behavior | Others |
|---------|------|---------------|--------|
| Abstract base classes | No | **Yes** (Box, PumpBase, Presenter, Model, GUI, VisualStimBase) | No |
| Callback ownership | Hardcoded in BehavBox.\_\_init\_\_ | **Delegated to Presenter** via set_callbacks() | Hardcoded in BehavBox.\_\_init\_\_ |
| GUI in BehavBox | Yes (pygame + matplotlib) | **Separated** (gui.py / pyqtgui.py) | Yes |
| Lick debouncing | No | **Yes** (configurable min/max time, threshold) | No |
| Flipper barcode | No | **Yes** (32-bit serial barcode for ephys sync) | No |
| Configurable lick polarity | No (hardcoded True) | **Yes** (session_info["lick_input_setting"]) | No |
| Ephys rig support | No | **Yes** (dedicated IP, picamera2) | No |
| Off-Pi mock | No | **Yes** (dummy_box.py) | No |
| Syringe pump support | No | No | **Yes** (benville_gonogo/ssrt) |

> **Lick callback inversion:** This is a critical semantic decision. On main, `when_pressed = exit` (inverted). Matt's branch reverses this to `when_pressed = entry`. Matt also added a configurable `lick_input_setting` that controls the `active_state` of the Button, which effectively determines the polarity. **The unified library must make this explicit and configurable** -- the meaning of "pressed" depends on the electrical wiring of each specific box.

---

## 6. Head-Fixed vs. Freely-Moving: Do We Need Two Configurations?

### What's actually different?

**Head-Fixed Configuration:**
- Up to 3 lick sensors (left, right, center)
- Up to 5 IR sensors
- 2-4 sound outputs
- 4 cue LEDs (PWM)
- Solenoid valve pumps
- Treadmill (I2C)
- Visual gratings (rpg library)

*Branches: main, matt-behavior, headfixed_soyounk, treadmill_only*

**Freely-Moving Configuration:**
- 0-3 lick sensors (sometimes repurposed as sound outputs)
- 0-3 IR nosepoke sensors
- 2-5 sound outputs
- 3-4 cue LEDs
- Solenoid valves **or** syringe pump steppers
- No treadmill
- Visual gratings (optional)

*Branches: mitchfarrell-context, benville_gonogo, ssrt_task*

### Recommendation: One class, declarative configuration -- no internal "modes"

> **The differences are not about two distinct hardware designs -- they're about which subset of a common set of GPIO pins each experimenter needs.** The physical GPIO header is the same in both cases. The only real hardware difference is the pump type (solenoid vs. stepper).

Rather than having a `configuration="headfixed"` / `configuration="freemoving"` switch that selects between two internal code paths, the unified BehavBox should:

1. **Declare all possible GPIO resources** (lick sensors, IR sensors, sound outputs, cue LEDs, pumps, DIO lines) with their default pin assignments
2. **Let `session_info` enable/disable each resource** -- if a user doesn't need lick3, they set `"lick3": False` (or omit it), and that pin is never initialized
3. **Allow pin remapping** -- if a user wants GPIO 15 as a sound output instead of a lick sensor, they can configure that
4. **Support multiple pump backends** (solenoid and stepper) selected via configuration

This avoids the problem of proliferating "modes" as new configurations are needed. It also means that the head-fixed and freely-moving setups are just two different `session_info` configurations, not two branches of code.

---

## 7. Unification Plan

### 7.1 New repository: `behavbox`

The new package will be installable via `pip install -e ./behavbox` (or from a git URL). Proposed structure:

```
behavbox/
  pyproject.toml
  README.md
  src/
    behavbox/
      __init__.py          # public API: BehavBox, Pump, BoxLED, FlipperOutput, Treadmill
      box.py               # BehavBox class
      pump.py              # Pump base + SolenoidPump + SyringePump
      led.py               # BoxLED (PWMLED subclass)
      flipper.py           # FlipperOutput with barcode support
      treadmill.py         # Treadmill (I2C)
      adc.py               # ADS1x15 driver
      visualstim.py        # VisualStim (rpg gratings)
      platform.py          # auto-detect RPi vs desktop, patch gpiozero if needed
      config.py            # default pin maps, configuration validation
      mock/
        __init__.py        # mock_gpiozero (absorbed from mock-gpiozero package)
        devices.py         # Mock LED, Button, PWMLED, DigitalOutputDevice
        keyboard_sim.py    # KeyboardSimulator (tkinter subprocess)
        event_sim.py       # programmatic event injection
        pin_logger.py      # pin state change log
        _tk_window.py      # tkinter subprocess window
```

### 7.2 Incorporating changes from each branch

| Feature / Change | Origin Branch | Plan |
|------------------|---------------|------|
| Abstract base classes (Box, PumpBase, etc.) | matt-behavior | **Adopt.** Clean interface contracts are valuable. Simplify where possible (not every task needs a full Presenter/Model split) |
| Callbacks delegated to Presenter | matt-behavior | **Adopt, with modification.** BehavBox should provide a `set_callbacks(handler)` method, but also support simple direct callback assignment for lightweight use cases |
| GUI separated from BehavBox | matt-behavior | **Adopt.** GUI/plotting has no place in the hardware layer |
| Configurable lick polarity | matt-behavior | **Adopt.** Via `session_info["lick_active_state"]` (True/False) |
| Lick debouncing | matt-behavior | **Adopt as optional feature.** Configurable via `session_info["lick_debounce_ms"]`, disabled by default (0) |
| FlipperOutput barcode | matt-behavior | **Adopt.** Via `session_info["emit_barcodes"]` flag (default False) |
| FlipperOutput base class LED (not DigitalOutputDevice) | matt-behavior | **Adopt.** LED provides `toggle()` and `is_active` |
| Ephys rig support | matt-behavior | **Adopt.** Via `session_info["ephys_rig"]` flag |
| Syringe pump stepper motor support | benville_gonogo/ssrt | **Adopt.** New `SyringePump` class alongside existing `SolenoidPump`, selected via `session_info["pump_type"]` |
| Semantic IR callback names (left_IR_entry vs IR_1_entry) | benville_gonogo | **Keep numeric naming.** The physical IR sensor positions are not inherently "left" or "right" -- that's a task-level mapping. The hardware layer should use `IR_1`, `IR_2`, etc. |
| Extra sound outputs on GPIO 9, 15 | headfixed_soyounk | **Support via configuration.** Sound outputs are just LED objects; let users configure which pins are sound triggers |
| Hardcoded tube_fit pump calibration | mitchfarrell-context | **Deprecate.** All pump calibration should use `session_info` coefficients. A simple flow-rate model can be a special case of the linear model (slope=1/flow_rate, intercept=0) |
| reserved_rx generic button inputs | mitchfarrell, treadmill_only | **Support via configuration.** Any DIO or unused sensor pin can be configured as a generic button input |
| FlipperOutput header typo ("pin_tate") | main | **Fix.** |

### 7.3 Declarative pin configuration

BehavBox's `__init__` will read a `"hardware"` dict from `session_info` to determine which devices to initialize. Example:

```python
session_info["hardware"] = {
    # Lick sensors (set to False or omit to disable)
    "lick1": {"pin": 26, "active_state": True},   # left
    "lick2": {"pin": 27, "active_state": True},   # right
    "lick3": {"pin": 15, "active_state": True},   # center (set False to use as sound)

    # IR sensors (set to False or omit to disable)
    "IR_rx1": {"pin": 5},
    "IR_rx2": {"pin": 6},
    "IR_rx3": {"pin": 12},
    "IR_rx4": {"pin": 13},   # omit this for mitchfarrell config
    "IR_rx5": {"pin": 16},

    # Cue LEDs
    "cueLED1": {"pin": 22, "pwm": True, "frequency": 200},
    "cueLED2": {"pin": 18, "pwm": True, "frequency": 200},
    "cueLED3": {"pin": 17, "pwm": True, "frequency": 200},
    "cueLED4": {"pin": 14, "pwm": True, "frequency": 200},

    # Sound outputs (accent pins as needed)
    "sound1": {"pin": 23},
    "sound2": {"pin": 24},
    # "sound3": {"pin": 15},  -- would conflict with lick3; disable lick3 first

    # Digital I/O
    "DIO4": {"pin": 10, "direction": "output"},
    "DIO5": {"pin": 11, "direction": "output"},

    # Pump configuration
    "pump_type": "solenoid",  # or "syringe"
    "pumps": {
        "1": {"pin": 19},
        "2": {"pin": 20},
        "3": {"pin": 21},
        "4": {"pin": 7},
        "air":    {"pin": 8},
        "vacuum": {"pin": 25},
    },

    # Peripherals
    "flipper":   {"pin": 4, "emit_barcodes": False},
    "treadmill": {"enabled": True, "i2c_bus": 1, "i2c_address": 0x08},
    "visual_stimulus": False,
}
```

For backwards compatibility, if `session_info["hardware"]` is absent, BehavBox falls back to the current main-branch defaults. This lets existing session_info files work without modification during the transition.

### 7.4 Pump unification

```python
class PumpBase(ABC):
    @abstractmethod
    def reward(self, which_pump: str, reward_size: float) -> None: ...
    @abstractmethod
    def toggle(self, which_pump: str) -> None: ...

class SolenoidPump(PumpBase):
    """Solenoid valve pumps with linear calibration coefficients."""
    # duration = slope * (reward_size / 1000) + intercept

class SyringePump(PumpBase):
    """Stepper motor syringe pumps with volumetric calculation."""
    # steps = volume / (pi * (diameter/2)^2 * distance_per_step)
```

Selected via `session_info["hardware"]["pump_type"]`. Both share the same `reward(which_pump, reward_size)` interface so task code doesn't change.

---

## 8. Platform Auto-Detection

The new package will **automatically detect the platform** and use real or mock GPIO. No more try/except bootstrap in every script.

```python
# behavbox/platform.py
import platform, os

def is_raspberry_pi() -> bool:
    """Detect if running on a Raspberry Pi."""
    if platform.machine().startswith("aarch64") or platform.machine().startswith("arm"):
        # Check for RPi-specific indicators
        try:
            with open("/proc/device-tree/model") as f:
                return "raspberry pi" in f.read().lower()
        except FileNotFoundError:
            pass
    return False

def setup_gpio():
    """Import real gpiozero on RPi, mock on everything else."""
    if is_raspberry_pi():
        import gpiozero  # real hardware
    else:
        from behavbox.mock import patch
        patch()  # sets sys.modules['gpiozero'] to mock
```

`behavbox/__init__.py` will call `setup_gpio()` at import time, so simply doing `import behavbox` handles everything. The existing `try: import mock_gpiozero; mock_gpiozero.patch()` pattern in task scripts can be removed.

> **Platform coverage:**
> - **Raspberry Pi (aarch64/armv7l + /proc/device-tree/model):** real gpiozero
> - **macOS (darwin):** mock (KeyboardSimulator uses subprocess for tkinter compatibility)
> - **x86-64 Linux:** mock
> - **WSL (Windows Subsystem for Linux):** mock (detected by absence of /proc/device-tree/model)

---

## 9. Migration Path

### Phase 1: Create the new `behavbox` package

1. Create new repository `behavbox`
2. Port `essential/` files from main, incorporating the changes listed in Section 7.2
3. Absorb `mock-gpiozero/` into `behavbox/mock/`
4. Add platform auto-detection
5. Add declarative pin configuration with backwards-compatible defaults
6. Unify pump classes (solenoid + syringe)
7. Write tests using the built-in mock

### Phase 2: Update this repository (RPi4_behavior_boxes)

1. Add `behavbox` as a dependency
2. Remove `essential/` directory
3. Remove `mock-gpiozero/` directory
4. Remove `try: import mock_gpiozero` bootstrap from all scripts
5. Update imports: `from behavbox import BehavBox, Pump`
6. Ensure all existing task protocols work with the new package

### Phase 3: User migration

1. Each user installs the `behavbox` package: `pip install -e /path/to/behavbox`
2. Each user creates their own task repository (or continues using a branch of RPi4_behavior_boxes for tasks)
3. Users update their `session_info` files to include a `"hardware"` section if they need non-default pin configurations
4. Users with the freely-moving configuration provide their specific `"hardware"` config; users with the standard head-fixed setup can use defaults unchanged

---

*Generated by Claude Code -- February 2026*
