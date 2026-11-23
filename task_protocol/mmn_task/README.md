# Visual MMN oddball task

This passive protocol presents mismatch-negativity (MMN) visual oddball and
control blocks. It does not initialize the behavior box or optogenetic outputs.

The default schedule is **15 minutes of spontaneous gray background →
(oddball A → oddball B → control) × 3**, nine stimulus blocks:

Set `block_order` in `session_info.py` to choose the three-block cycle:

```python
session_info['block_order'] = ('oddball_A', 'oddball_B', 'control')
# Or use: ('control', 'oddball_A', 'oddball_B')
```

With `block_count=9`, either order repeats three times. The initial 15-minute
gray period always precedes the first stimulus block, including control when
control comes first. Oddball A/B retain their standard/deviant identities in
both orders. Test mode also follows the selected order.

| Block type | Stimuli |
| --- | --- |
| Oddball A | 135° standard, 45° deviant; 96 trials of eight gratings |
| Oddball B | 45° standard, 135° deviant; 96 trials of eight gratings |
| Control | 640 single-grating trials; 80 of each of eight angles, shuffled |

The control angles are 22.5°, 45°, 67.5°, 90°, 112.5°, 135°, 157.5°, and 180°.
Each control block is shuffled separately; adjacent repeats are allowed.
Oddball trials contain 4, 5, 6, or 7 standards before one deviant (balanced
within each block), followed by standards in any remaining positions.

The spontaneous period runs once, after grating generation/preloading and
before the first stimulus block. The display stays at its gray background for
900 seconds without gratings. Its measured start/end times and completion or
interruption status are saved under `spontaneous` in the session JSON metadata.
Ctrl+C stops the session during this period; Pygame also supports Escape/close.

All blocks use a 0.5-second stimulus and a 0.7-second gray interval. Blocks are
separated by 120 seconds. The full schedule contains 6,528 grating
presentations. The CSV records `block_type` and `repetition`; control trials
have `stimulus_type=control`, `sequence_position=1`, and an empty
`standards_before_deviant` field.

## Saved stimulus sequence

Each run saves the full planned presentation order before opening the display
or starting the spontaneous period. The default destination is:

```text
~/experimental_data/mmn/task_output/mmn_stimulus_sequence_YYYYMMDD_HHMMSS.csv
```

The file contains one row per grating across every oddball and control block
(6,528 rows for the default full session), with `stimulus_index`, block type,
repetition, trial, within-trial position, standard/deviant/control identity,
`orientation_deg`, and `grating_id`. It exports the same randomized schedule
used for presentation, even when `random_seed=None`.

| Angle in degrees | Grating ID |
| --- | --- |
| 22.5 | 1 |
| 45 | 2 |
| 67.5 | 3 |
| 90 | 4 |
| 112.5 | 5 |
| 135 | 6 |
| 157.5 | 7 |
| 180 | 8 |

The ID mapping is fixed for both oddball and control stimuli: 45° always has
ID 2, and 135° always has ID 6. If you configure other angles, their degrees
are saved with an empty ID.

The timed `mmn_events_*.csv` log also contains `stimulus_index` and `grating_id`,
so its rows can be matched to the plan. For an interrupted session, use its
timestamps/status to identify presentations that actually ran; the sequence
file preserves the entire planned order. The JSON metadata records the
sequence filename, planned count, and ID-to-angle mapping.

Set `task_output_dir` in `session_info.py` to choose a different sequence
directory. Its default, `'task_output'`, is relative to `output_dir`, so
`--output-dir PATH` also moves this subfolder. An absolute `task_output_dir`
is used directly.

## Configure the session

Edit the repository-root `session_info.py` before each session. Like
`matt-behavior/main.py`, the runner calls `make_session_info()` to get the session
settings. Set `mouse_name`, `output_dir`, the MMN schedule, and visual settings
there. The effective settings, including command-line overrides, are saved in
the session JSON metadata.

The default Pi configuration uses the same `rpg.Screen()` framebuffer backend
as `matt-behavior`: full-frame, precomputed sine-wave gratings, a 1280-by-720
framebuffer, and gray level 40 between stimuli. Oddball gratings use 45°/135°;
control blocks use all eight angles above. The MMN
duration remains 0.5 seconds, the gray interval remains 0.7 seconds, and the
requested drift frequency remains 2 Hz. It does not reuse the horizontal or
vertical grating files from the behavior task.

The Pi settings in `session_info.py` are:

| Setting | Meaning |
| --- | --- |
| `output_dir` | Session event-log and metadata directory |
| `task_output_dir` | Planned-sequence directory; default `'task_output'` inside `output_dir` |
| `spontaneous_duration_s` | Initial gray-background period in seconds; default 900 (15 minutes), 0 to skip |
| `block_order` | Cycle order: A → B → control, or control → A → B |
| `block_count` | Total blocks; default 9, repeating the selected cycle three times |
| `orientations_deg` | Standard/deviant angles; default `(45, 135)` |
| `trials_per_block` | Eight-grating trials per oddball block; default 96 |
| `control_trials_per_block` | Single-grating control trials per block; default 640 |
| `control_orientations_deg` | Eight angles from 22.5° through 180° |
| `grating_duration` | Stimulus duration in seconds |
| `inter_grating_interval` | Gray interval in seconds |
| `temporal_frequency_hz` | Requested drift frequency in Hz |
| `spatial_frequency_cycles_per_degree` | RPG spatial frequency; default 0.2 |
| `gray_level` | Inter-stimulus gray level, 0–255; default 40 |
| `photodiode_patch_enabled` | Show the bottom-left synchronization patch; default `True` |
| `photodiode_patch_size_px` | Patch `(width, height)` in framebuffer pixels; default `(80, 40)` |
| `grating_resolution` | Framebuffer/file `(width, height)` in pixels |
| `screen_width_degrees` | Visual angle across the screen width; default 80° |
| `refresh_rate_hz` | Actual monitor refresh rate; default 60 Hz |
| `gratings_dir` | Cache directory for the generated MMN files |

Spatial frequency for the Pi backend is in **cycles per degree**. Set
`screen_width_degrees` to the visual angle covered by your stimulus screen,
and `refresh_rate_hz` to its actual refresh rate. The default 80° is the
upstream RPG screen-angle default; match your rig's calibration. These are
separate from the Pygame reference's cycles-per-centimeter settings.

The upstream [RPG builder source](https://github.com/SjulsonLab/rpg/blob/master/rpg/_rpigratings.c)
truncates fractional angles. MMN therefore generates native RGB565 grating files
with NumPy, preserving the exact angles and requested drift frequency, and
loads/plays them using the working `rpg.Screen` methods. The generator uses
one frame at a time; all eight movies are preloaded before timing starts.
The default cache and loaded movie data, including the gray frame, occupy about
424 MiB each.

Files are built automatically on first use. Changing angles, duration,
frequency, screen calibration, refresh rate, or resolution selects new cache
files. This generator uses a separate cache signature from the old RPG-built
files. Stimulus duration is rounded to the nearest whole display frame.

## Synchronization patch

Both the Pi/RPG and Pygame displays show an **80-by-40-pixel patch at the
bottom-left** by default. It is white throughout gray periods (spontaneous,
inter-stimulus, and inter-block), and black throughout each grating, including
control stimuli. Each grating onset/offset produces a patch transition even
when successive gratings have the same angle.

Set `photodiode_patch_enabled=False` to disable it or edit
`photodiode_patch_size_px=(80, 40)` in `session_info.py` to resize it. Sizes are
framebuffer pixels and must fit inside the display. The session metadata saves
the patch rectangle and white/black intensity levels. At 1280-by-720 resolution,
the default rectangle is `(x=0, y=680, width=80, height=40)` using a top-left origin.

On the Pi, the black patch is baked into every grating frame, so it changes
with the first displayed stimulus frame. The white patch is part of a cached
gray frame displayed for two refreshes, then held until the next stimulus.
Changing patch settings selects new cache files automatically.

## Run on the Pi

From the repository root, use the same Pi environment and display setup in
which `matt-behavior/main.py` works:

```bash
python3 main.py
```

The module entry point, `python3 -m task_protocol.mmn_task.run_mmn_task`, also
loads `session_info.py`. No desktop session or SDL monitor selection is needed
for RPG; it uses `/dev/fb0`, just like the working behavior task. Stop with
Ctrl+C.

For a shortened cycle (five seconds of spontaneous gray, one eight-grating
trial per oddball block, one presentation of each control angle, and five
seconds between blocks):

```bash
python3 main.py --test-mode
```

Session CSV/JSON files are written under `output_dir` (by default,
`~/experimental_data/mmn`). Use `--output-dir PATH` or `--seed N` to override
the corresponding session setting for a run. Optogenetic outputs remain
disabled. RPG retains its own native frame-output behavior.

## Desktop/Pygame check

For a windowed check without the Raspberry Pi framebuffer:

```bash
python3 main.py --windowed --test-mode
```

`--windowed` selects Pygame. For fullscreen Pygame on the second SDL display,
use `--backend pygame --display 1`. You can also set `visual_backend`,
`windowed`, and `display_index` in `session_info.py`. Set `windowed=False`
when using RPG. Pygame retains the original MATLAB-reference grating geometry
and gray level 128; RPG uses full-frame gratings and the configured gray level.
Both use the bottom-left synchronization patch settings from `session_info.py`.

## Pygame second-monitor preview

From a terminal on the Raspberry Pi desktop, run:

```bash
python3 -m task_protocol.mmn_task.test_grating
```

This separate Pygame utility shows a fullscreen, 45-degree drifting grating on SDL display index 1
(the second display) for 10 seconds, then returns to the terminal. Use
`--display 0` to select the first display, `--seconds 20` to change the preview
duration, or `--windowed` for a windowed check. This is only a display test; it
does not load `session_info.py`, run the MMN schedule, or write session logs.
Use `main.py --test-mode` to check the configured Pi backend.

## Diagnose desktop/display setup

If the Pi still boots to a text console, run this diagnostic from the repository
root:

```bash
python3 -m task_protocol.mmn_task.check_display
```

It reports the boot target, display-manager and desktop-package status, DRM
connector status, and (when run inside an X desktop session) the `xrandr`
layout. It does not change system settings or install packages.

The Pygame renderer uses the MATLAB reference's spatial/temporal frequencies, grating
size, screen offset, and photodiode patch placement. The reference sets the
Gabor sigma to zero, so this implementation uses an unwindowed sinusoidal
grating. The photodiode patch changes from white during the gray interval to
black during each stimulus. The CSV records stimulus identity and software
onset/offset times. For RPG, onset is sampled immediately before its blocking
display call, and offset after the gray display call returns. These are software
estimates, not photodiode measurements. The metadata records this timing
convention and the selected backend; RPG's integer-second Unix timestamp is
not used for subsecond onset logging.

Display timing and monitor geometry must be checked on the actual
Raspberry Pi/display setup before experimental use. In particular, verify
grating position, photodiode patch placement, refresh timing, and logged
stimulus durations with the intended display and acquisition system.
