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
~/experimental_data/mmn/<mouse>_YYYYMMDD_HHMMSS_microseconds/task_output/mmn_stimulus_sequence_YYYYMMDD_HHMMSS.csv
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
directory. Its default, `'task_output'`, is inside the dated session folder, so
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
| `output_dir` | Parent directory for the dated session folders |
| `task_output_dir` | Planned-sequence directory; default `'task_output'` inside each session folder |
| `camera_enabled` | Start the configured camera Pi recorders; default `False` until configured |
| `camera_nodes` | Camera hosts, SSH usernames, camera backends and video settings |
| `treadmill` | Copy an existing treadmill file during the session; default `False` until configured |
| `treadmill_setup` | Source file path, header count and file-copy options |
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
Ctrl+C during recording. When camera recording is enabled, the initial camera
adjustment step uses Ctrl+C to continue to recording, as described below.

For a shortened cycle (five seconds of spontaneous gray, one eight-grating
trial per oddball block, one presentation of each control angle, and five
seconds between blocks):

```bash
python3 main.py --test-mode
```

Each run creates a new `<mouse>_YYYYMMDD_HHMMSS_microseconds` folder under
`output_dir` (by default, `~/experimental_data/mmn`). Use `--output-dir PATH` or `--seed N` to override
the corresponding session setting for a run. Optogenetic outputs remain
disabled. RPG retains its own native frame-output behavior.

## Camera and treadmill recording

Enable recording in the repository-root `session_info.py` after setting the
rig's camera host and existing treadmill file path. Recording starts before
the 15-minute spontaneous period and stops after the final stimulus or on
interruption. Recorders run in separate processes so the native RPG display
calls cannot block data capture. An enabled recorder that cannot start prevents
the timed session from starting; a recorder that exits during the task aborts
the session and is reported in the metadata.

### Adjust the camera, then press Ctrl+C to start recording

With `camera_enabled=True`, `python3 main.py` first opens a live camera preview
on the camera Pi. **MMN saves no camera video or treadmill copy during this
adjustment step.** Adjust the camera, then press **Ctrl+C in the stimulus Pi
terminal running main.py** when it says `START RECORDING`.

MMN closes the adjustment preview and releases the camera, prepares the stimulus
display, then starts camera/treadmill recording and the configured spontaneous
gray period. A new dated session folder is created after the adjustment step.
The time spent adjusting the camera is excluded from the spontaneous period
and session recording duration. Startup, rendering or cleanup failures prevent
the session from starting. Ctrl+C before the preview becomes ready cancels
startup; Ctrl+C after recording begins aborts the session normally.

The adjustment step defaults to DRM preview for this rig's attached camera-Pi
monitor; an explicit `preview_backend='qt'` or `'qtgl'` is also honored. Keep
LightDM stopped on the camera Pi while using DRM, including throughout the
recording if its preview is enabled. The node's `preview` flag still controls
whether the preview is shown **during** recording.

Both full sessions and `--test-mode` include this adjustment step when camera
recording is enabled. `--no-recording` skips it. To skip adjustment while still
recording camera video, add this inside `make_session_info()` before `return`:

```python
    session_info['camera_preview_before_recording'] = False
```

All files are grouped in the dated session folder:

```text
~/experimental_data/mmn/<mouse>_YYYYMMDD_HHMMSS_microseconds/
    mmn_events_*.csv
    mmn_metadata_*.json
    task_output/mmn_stimulus_sequence_*.csv
    treadmill.csv
    treadmill_copy_times.csv
    acquisition/                 # Treadmill config, worker log and result
    recording_result.json
    video/cam0/
        video.h264
        frames.csv
        recording_result.json
        acquisition/             # Camera config and worker log
```

Treadmill files appear only when `treadmill=True`; camera files appear only
when `camera_enabled=True`. Metadata records the effective settings, worker
status, source paths, output paths and failures.

### Existing treadmill CSV

The `matt-behavior` task writes `<session_name>_treadmill.csv` using a GPIO
encoder. For this rig's independently recorded treadmill file, MMN instead
opens the existing source read-only and copies new bytes into `treadmill.csv`:

```python
session_info['treadmill'] = True
session_info['treadmill_setup'] = {
    'backend': 'file',
    'source_file': '/absolute/path/to/the/active/treadmill.csv',
    'source_header_lines': 1,
    'include_existing_data': False,
    'poll_interval_s': 0.05,
}
```

Start the existing treadmill writer before MMN, and ensure it flushes data
during recording. MMN does not start or stop that program. By default it copies
the header and only data appended after its worker starts, skipping old rows.
Set `source_header_lines=0` for a headerless file; set
`include_existing_data=True` if a newly created source already contains data
you want to keep. Source values, delimiters, units and timestamps are preserved.
Naming the copy `.csv` does not convert a differently formatted source.

`treadmill_copy_times.csv` records byte offsets and receipt times for each
copied chunk. Those times are not per-sample measurement timestamps; use the
source's timestamps or the treadmill analog signal in the electrophysiology
recording for analysis. A missing source fails startup; replacing or truncating
it during the session fails recording. A source that produces no new bytes
is reported with a warning in the worker metadata.

### Separate camera Pi

The camera entry uses the supplied address `pi@10.49.98.252` with `picamera2`.
Check SSH/library access with the diagnostic below, then set `camera_enabled=True`.
Use `backend='picamera'` for the older PiCamera library; set `transport='local'`
only if the camera is connected to the stimulus Pi.

The stimulus Pi needs `ssh` and `rsync`, and working noninteractive SSH access
to the camera Pi. The camera Pi needs the selected Python camera library and
`rsync`. MMN stages its standalone worker in a new recording folder on that Pi;
the camera Pi does not need a checkout of this branch. Recording uses no preview
window by default. Readiness requires camera timestamps and nonempty video output.

The camera first saves under
`<remote_output_dir>/<session_name>/video/<camera_id>/` on its own Pi. After all
recorders stop, MMN uses `rsync` to copy the recording into the matching local
session folder. Remote files are retained. A failed copy marks the session
failed and records the remote location so the recording can be recovered.
Video transfer adds time after stimulation ends.

`frames.csv` contains frame indices, sensor timestamps (nanoseconds for
Picamera2, microseconds for PiCamera), wall-clock epoch seconds and camera-Pi
monotonic times. Picamera2 records metadata for camera requests; the video
encoder can drop frames. Monotonic clocks on separate Pis cannot be compared
directly. Wall-clock comparison requires synchronized clocks; these software
timestamps do not establish hardware synchronization with electrophysiology.

To check camera SSH/library availability and locate existing treadmill files
without starting recording, run this on the stimulus Pi:

```bash
python3 -m task_protocol.mmn_task.check_acquisition --check-camera
```

The file search prints active treadmill-related log handles and recent
treadmill/Teensy/wheel file candidates. It is bounded and does not select a
source automatically. Add `--search-root /path/to/recordings` to search a
specific directory. Set the verified source path in `session_info.py`.

Test the configured recordings with `python3 main.py --test-mode`. For a visual
check with recording temporarily disabled, use:

```bash
python3 main.py --test-mode --no-recording
```

### Live camera preview for adjustment

To adjust camera position or focus before recording, choose the mode for the
camera Pi's screen. Run these commands from the **stimulus Pi's** repository root.

If the camera Pi's attached monitor shows a **text console/login prompt**, use
the direct-monitor preview:

```bash
python3 -m task_protocol.mmn_task.camera_preview --backend drm
```

This uses Picamera2's [DRM preview](https://github.com/raspberrypi/picamera2/blob/main/picamera2/previews/drm_preview.py)
to render on the camera Pi's physical monitor. It does not require an X desktop,
`DISPLAY`, or Qt. The camera user must have access to the DRM display device.

If the camera Pi has a **graphical desktop** on its monitor or remote desktop,
use the Qt preview:

```bash
python3 -m task_protocol.mmn_task.camera_preview --backend qt
```

The window opens on the configured camera Pi (`pi@10.49.98.252`), using the
camera settings in `session_info.py`. This command works even when
`camera_enabled=False`. It starts no MMN stimuli and saves no video. It keeps
only worker configuration/logs in temporary directories. Press **Ctrl+C in the
stimulus Pi terminal** to close the preview and release the camera before
running `python3 main.py` or `python3 main.py --test-mode`.

To also show the preview while MMN records, add these assignments in
`session_info.py`, inside `make_session_info()` before its `return`:

```python
    session_info['camera_enabled'] = True
    session_info['camera_nodes'][0]['preview'] = True
    session_info['camera_nodes'][0]['preview_backend'] = 'drm'  # Attached monitor showing a text console.
```

For a graphical desktop, use these settings instead:

```python
    session_info['camera_nodes'][0]['preview_backend'] = 'qt'
    session_info['camera_nodes'][0]['preview_display'] = ':0'
```

Both test mode and full sessions honor this option. The preview and video
recording share one camera instance.

For Qt preview, `preview_display` defaults to `':0'`. To find the correct value, run
`echo "$DISPLAY"` in a terminal **inside the camera Pi's desktop/remote
desktop**. If it reports `:1`, set `preview_display=':1'` in the camera entry,
or use this for the adjustment command:

```bash
python3 -m task_protocol.mmn_task.camera_preview --display :1
```

The Qt preview (`preview_backend='qt'`) renders in the
desktop window for remote viewing. Its Qt dependencies and a logged-in
X11/Xwayland desktop must be available on the camera Pi. The worker selects
the camera Pi's `DISPLAY` and uses `~/.Xauthority` when available. If the
desktop uses a different authentication file, set `preview_xauthority` in the
camera entry or pass `--xauthority /path/on/camera/pi` to the adjustment command.
No desktop permissions are changed. `preview_window=(0, 0, 640, 480)` controls
the image's x, y, width and height in camera Pi screen pixels for both modes.

For multiple camera entries, choose one with `--camera cam0`. A startup error
prints the camera worker's log in the stimulus Pi terminal. An unavailable
requested preview fails startup, rather than silently running without a window.

If DRM reports `commit failed`, camera frames can still be arriving while the
monitor update fails. MMN reports that rendering failure even if the worker is
still alive. A desktop/display service may be holding the display; check its
status on the camera Pi with `systemctl status display-manager --no-pager`.
Changing `preview_display` does not select a different physical display in DRM
mode. Native messages without newlines are kept in the worker log and cannot
hide the camera readiness/result messages.

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
