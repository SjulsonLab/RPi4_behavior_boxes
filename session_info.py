"""Edit these settings before starting a passive visual MMN session."""

import socket
from pathlib import Path
from typing import Any, Dict


def make_session_info() -> Dict[str, Any]:
    """Return a fresh settings dict; durations are seconds and angles are degrees."""
    session_info = {}

    # Session identity and saving, using the same entry point as matt-behavior.
    session_info['mouse_name'] = 'test-mouse'
    session_info['box_name'] = socket.gethostname()
    session_info['task_config'] = 'mmn'
    session_info['output_dir'] = str(Path.home() / 'experimental_data' / 'mmn')
    session_info['task_output_dir'] = 'task_output'  # Relative to output_dir, or an absolute path.

    # Record spontaneous activity on gray before the first stimulus block.
    session_info['spontaneous_duration_s'] = 15 * 60  # Seconds; 0 skips this period.

    # Choose one cycle; nine blocks repeat the selected order three times.
    session_info['block_order'] = ('oddball_A', 'oddball_B', 'control')
    # For control first, use: ('control', 'oddball_A', 'oddball_B')
    session_info['block_count'] = 9
    session_info['trials_per_block'] = 96  # Eight-stimulus trials per oddball block.
    session_info['stimuli_per_trial'] = 8
    session_info['standard_count_options'] = (4, 5, 6, 7)
    session_info['orientations_deg'] = (45, 135)
    # One grating per control trial; 80 of each angle, shuffled within each block.
    session_info['control_trials_per_block'] = 640
    session_info['control_orientations_deg'] = (22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180)
    session_info['grating_duration'] = 0.5
    session_info['inter_grating_interval'] = 0.7
    session_info['inter_block_interval_s'] = 120.0
    session_info['temporal_frequency_hz'] = 2.0
    session_info['random_seed'] = None  # Set an integer for repeatable trial order.

    # Pi framebuffer settings, matching the rpg setup used by matt-behavior.
    session_info['visual_backend'] = 'rpg'  # 'rpg' on the Pi; 'pygame' for desktop.
    session_info['gratings_dir'] = str(Path.home() / 'gratings' / 'mmn')
    session_info['grating_resolution'] = (1280, 720)  # (width, height), in pixels.
    session_info['screen_width_degrees'] = 80.0  # Visual angle across the screen width; calibrate for the rig.
    session_info['refresh_rate_hz'] = 60  # Must match the stimulus monitor refresh rate.
    session_info['gray_level'] = 40  # Between stimuli, from 0 to 255.
    # Bottom-left synchronization patch: white on gray, black during gratings.
    session_info['photodiode_patch_enabled'] = True
    session_info['photodiode_patch_size_px'] = (80, 40)  # (width, height), framebuffer pixels.
    session_info['spatial_frequency_cycles_per_degree'] = 0.2

    # Desktop/Pygame settings only; rpg presents full-frame gratings on /dev/fb0.
    session_info['windowed'] = False
    session_info['display_index'] = 0  # Zero-based SDL monitor index.
    session_info['pixels_per_cm'] = 36.127
    session_info['grating_size_cm'] = 30.0
    session_info['grating_top_cm'] = 23.0
    session_info['spatial_frequency_cycles_per_cm'] = 0.2
    return session_info
