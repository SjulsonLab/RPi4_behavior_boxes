# Visual MMN oddball task

This passive protocol presents the mismatch-negativity (MMN) visual oddball
blocks from the MATLAB reference without the optogenetic, spontaneous-activity,
or orientation-tuning blocks. It does not initialize the behavior box or any
opto outputs/triggers.

The default schedule has six blocks of 96 trials. Each trial contains eight
stimuli: 4, 5, 6, or 7 standards (balanced within each block), one deviant, and
standards in any remaining positions. The standard and deviant orientations
alternate between 135/45 degrees and 45/135 degrees by block. Gratings are
presented for 0.5 seconds followed by a 0.7-second gray interval; blocks are
separated by 120 seconds.

## Run

From the repository root:

```bash
python3 -m task_protocol.mmn_task.run_mmn_task
```

By default the display opens fullscreen and session CSV/JSON files are written
under `~/experimental_data/mmn`. Use `--output-dir PATH` to select another
location, `--seed N` for reproducible trial ordering, `--windowed` for a
windowed display, or `--test-mode` to present one short trial.

## Check the second monitor

From a terminal on the Raspberry Pi desktop, run:

```bash
python3 -m task_protocol.mmn_task.test_grating
```

This shows a fullscreen, 45-degree drifting grating on SDL display index 1
(the second display) for 10 seconds, then returns to the terminal. Use
`--display 0` to select the first display, `--seconds 20` to change the preview
duration, or `--windowed` for a windowed check. This is only a display test; it
does not run the MMN schedule or write session logs.

## Diagnose desktop/display setup

If the Pi still boots to a text console, run this diagnostic from the repository
root:

```bash
python3 -m task_protocol.mmn_task.check_display
```

It reports the boot target, display-manager and desktop-package status, DRM
connector status, and (when run inside an X desktop session) the `xrandr`
layout. It does not change system settings or install packages.

The renderer uses the MATLAB reference's spatial/temporal frequencies, grating
size, screen offset, and photodiode patch placement. The reference sets the
Gabor sigma to zero, so this implementation uses an unwindowed sinusoidal
grating. The photodiode patch changes from white during the gray interval to
black during each stimulus. The CSV records stimulus identity and measured
software onset/offset times; it does not generate digital synchronization
triggers.

Pygame display timing and monitor geometry must be checked on the actual
Raspberry Pi/display setup before experimental use. In particular, verify
grating position, photodiode patch placement, refresh timing, and logged
stimulus durations with the intended display and acquisition system.
