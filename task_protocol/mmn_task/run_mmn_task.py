#!/usr/bin/env python3
"""Run the passive visual MMN protocol without optogenetic outputs."""

import argparse
import csv
import json
import time
from dataclasses import asdict, fields, replace
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import Dict, Optional

from session_info import make_session_info
from task_protocol.mmn_task.acquisition import (
    RecordingDisplay, SessionAcquisition, create_session_directory,
)
from task_protocol.mmn_task.camera_preview import run_preview
from task_protocol.mmn_task.mmn_protocol import MMNConfig, StimulusEvent, build_schedule
from task_protocol.mmn_task.rpg_stimulus import RPGGratingDisplay
from task_protocol.mmn_task.stimulus_sequence import (
    GRATING_ANGLES_DEG, STIMULUS_COLUMNS, stimulus_row, write_stimulus_sequence,
)
from task_protocol.mmn_task.visual_stimulus import DriftingGratingDisplay


def _write_metadata(path: Path, metadata: Dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as output:
        json.dump(metadata, output, indent=2)
        output.write("\n")


def _present_spontaneous_period(
    display,
    duration_s: float,
    metadata: Dict[str, object],
    metadata_path: Path,
    session_start_monotonic: float,
    session_wall_start: float,
) -> bool:
    """Hold gray for duration_s seconds before block 1; return completion bool.

    display provides show_gray() and interruptible wait_until(monotonic seconds).
    Write phase start/end times relative to session_start_monotonic and matching
    ISO wall times to the session JSON at metadata_path, including on Ctrl+C.
    A zero duration records a skipped period and returns True immediately.
    """
    phase = {"requested_duration_s": duration_s, "status": "skipped"}
    metadata['spontaneous'] = phase
    if duration_s == 0:
        phase['actual_duration_s'] = 0.0
        _write_metadata(metadata_path, metadata)
        return True

    display.show_gray()
    onset = time.monotonic()
    phase.update(
        status='running',
        actual_onset_s=round(onset - session_start_monotonic, 6),
        onset_wall_time=datetime.fromtimestamp(
            session_wall_start + onset - session_start_monotonic
        ).astimezone().isoformat(timespec='microseconds'),
    )
    _write_metadata(metadata_path, metadata)
    print(f"Spontaneous gray background: {duration_s:g} seconds before block 1.", flush=True)
    completed = False
    try:
        completed = display.wait_until(onset + duration_s)
        return completed
    finally:
        offset = time.monotonic()
        phase.update(
            status='complete' if completed else 'aborted',
            actual_offset_s=round(offset - session_start_monotonic, 6),
            actual_duration_s=round(offset - onset, 6),
            offset_wall_time=datetime.fromtimestamp(
                session_wall_start + offset - session_start_monotonic
            ).astimezone().isoformat(timespec='microseconds'),
        )
        _write_metadata(metadata_path, metadata)


def _event_row(
    event: StimulusEvent,
    target_onset: float,
    actual_onset: Optional[float],
    actual_offset: Optional[float],
    block_start: float,
    session_start_monotonic: float,
    session_wall_start: float,
    status: str,
    stimulus_index: Optional[int] = None,
) -> Dict[str, object]:
    if actual_onset is None:
        actual_onset_s: object = ""
        onset_lateness_s: object = ""
        onset_wall_time: object = ""
    else:
        actual_onset_s = round(actual_onset - block_start, 6)
        onset_lateness_s = round(actual_onset - target_onset, 6)
        onset_wall_time = datetime.fromtimestamp(
            session_wall_start + actual_onset - session_start_monotonic
        ).astimezone().isoformat(timespec="microseconds")

    actual_duration: object = ""
    if actual_onset is not None and actual_offset is not None:
        actual_duration = round(actual_offset - actual_onset, 6)

    return {
        **stimulus_row(event, stimulus_index),
        "expected_onset_s": round(target_onset - block_start, 6),
        "actual_onset_s": actual_onset_s,
        "onset_lateness_s": onset_lateness_s,
        "actual_duration_s": actual_duration,
        "onset_wall_time": onset_wall_time,
        "opto_enabled": False,
        "status": status,
    }


def run_protocol(
    config: MMNConfig,
    output_dir: Path,
    windowed: bool = False,
    session_info: Optional[Dict[str, object]] = None,
) -> int:
    """Run config, saving to output_dir; return 0, 130 if interrupted, or 1 on failure.

    session_info is a settings dict from make_session_info(); config holds the
    effective schedule in seconds/degrees. windowed applies to Pygame only.
    """
    settings = dict(make_session_info() if session_info is None else session_info)
    settings.update(asdict(config))
    settings.update(
        grating_duration=config.stimulus_duration_s,
        inter_grating_interval=config.inter_stimulus_interval_s,
        output_dir=str(output_dir),
        windowed=windowed,
    )
    backend = settings['visual_backend']
    if backend == 'rpg' and windowed:
        raise ValueError("Windowed mode requires the pygame backend")
    if backend not in ('rpg', 'pygame'):
        raise ValueError("visual_backend must be 'rpg' or 'pygame'")
    output_dir.mkdir(parents=True, exist_ok=True)
    schedule = build_schedule(config)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"mmn_events_{session_id}.csv"
    metadata_path = output_dir / f"mmn_metadata_{session_id}.json"
    task_output_dir = Path(settings.get('task_output_dir', 'task_output')).expanduser()
    if not task_output_dir.is_absolute():
        task_output_dir = output_dir / task_output_dir
    task_output_dir.mkdir(parents=True, exist_ok=True)
    settings['task_output_dir'] = str(task_output_dir)
    sequence_path = task_output_dir / f'mmn_stimulus_sequence_{session_id}.csv'
    metadata: Dict[str, object] = {
        "session_id": session_id,
        "status": "starting",
        "opto_enabled": False,
        "session_info": settings,
        "stimulus_sequence_file": str(sequence_path),
        "stimulus_sequence_scope": "planned",
        "planned_stimulus_count": len(schedule),
        "grating_id_to_orientation_deg": {
            str(index): angle for index, angle in enumerate(GRATING_ANGLES_DEG, start=1)
        },
        "blocks": config.block_count,
        "block_order": list(config.block_types),
        "trials_per_block": config.trials_per_block,
        "control_trials_per_block": config.control_trials_per_block,
        "control_orientations_deg": list(config.control_orientations_deg),
        "stimuli_per_trial": config.stimuli_per_trial,
        "standard_count_options": list(config.standard_count_options),
        "orientations_deg": list(config.orientations_deg),
        "stimulus_duration_s": config.stimulus_duration_s,
        "inter_stimulus_interval_s": config.inter_stimulus_interval_s,
        "inter_block_interval_s": config.inter_block_interval_s,
        "spontaneous_duration_s": config.spontaneous_duration_s,
        "temporal_frequency_hz": config.temporal_frequency_hz,
        "random_seed": config.random_seed,
        "windowed": windowed,
    }
    if backend == 'rpg':
        metadata['visual_backend'] = 'rpg_precomputed_drifting_grating'
        metadata['spatial_frequency_cycles_per_degree'] = settings['spatial_frequency_cycles_per_degree']
    else:
        metadata.update(
            visual_backend='pygame_procedural_drifting_grating',
            spatial_frequency_cycles_per_cm=config.spatial_frequency_cycles_per_cm,
            pixels_per_cm=config.pixels_per_cm,
            grating_size_cm=config.grating_size_cm,
            grating_top_cm=config.grating_top_cm,
        )
    header = [
        *STIMULUS_COLUMNS,
        "expected_onset_s",
        "actual_onset_s",
        "onset_lateness_s",
        "actual_duration_s",
        "onset_wall_time",
        "opto_enabled",
        "status",
    ]

    # Persist the same schedule the display loop will consume, including when
    # random_seed is None or the run is stopped during the spontaneous period.
    write_stimulus_sequence(sequence_path, schedule)
    print(f"Stimulus sequence: {sequence_path}", flush=True)

    recordings = SessionAcquisition(settings, output_dir)
    metadata['acquisition'] = recordings.report
    aborted = False
    failed = False
    if backend == 'rpg':
        display = RPGGratingDisplay(
            config,
            Path(settings['gratings_dir']),
            spatial_frequency_cycles_per_degree=settings['spatial_frequency_cycles_per_degree'],
            gray_level=settings['gray_level'],
            resolution=tuple(settings['grating_resolution']),
            screen_width_degrees=settings['screen_width_degrees'],
            photodiode_patch_enabled=settings['photodiode_patch_enabled'],
            photodiode_patch_size_px=tuple(settings['photodiode_patch_size_px']),
        )
    else:
        display = DriftingGratingDisplay(
            config, windowed=windowed, display_index=settings['display_index'],
            photodiode_patch_enabled=settings['photodiode_patch_enabled'],
            photodiode_patch_size_px=tuple(settings['photodiode_patch_size_px']),
        )
    display = RecordingDisplay(display, recordings, clock=time.monotonic)
    metadata["display"] = display.display_settings
    metadata["status"] = "running"
    session_start_monotonic = time.monotonic()
    session_start_wall = time.time()
    try:
        _write_metadata(metadata_path, metadata)
        recordings.start()
        # Recording startup and first-frame readiness precede the timed gray
        # period. Camera/treadmill files include all spontaneous activity.
        session_start_monotonic = time.monotonic()
        session_start_wall = time.time()
        metadata["started_at"] = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
        _write_metadata(metadata_path, metadata)

        with csv_path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=header)
            writer.writeheader()
            output.flush()

            aborted = not _present_spontaneous_period(
                display,
                config.spontaneous_duration_s,
                metadata,
                metadata_path,
                session_start_monotonic,
                session_start_wall,
            )
            onset_interval = config.stimulus_onset_interval_s
            next_block_start = time.monotonic()
            stimulus_index = 0

            # Control blocks contain one grating per trial and have a different
            # event count from oddball blocks. Group by the actual block IDs.
            for block_number, block_group in groupby(schedule, key=lambda event: event.block_number):
                if aborted or not display.wait_until(next_block_start):
                    aborted = True
                    break

                block_events_list = list(block_group)
                block_start = time.monotonic()
                previous_actual_onset: Optional[float] = None

                for event_index, event in enumerate(block_events_list):
                    stimulus_index += 1
                    expected_onset = block_start + event_index * onset_interval
                    target_onset = (
                        expected_onset
                        if previous_actual_onset is None
                        else previous_actual_onset + onset_interval
                    )
                    if not display.wait_until(target_onset):
                        writer.writerow(
                            _event_row(
                                event,
                                target_onset,
                                None,
                                None,
                                block_start,
                                session_start_monotonic,
                                session_start_wall,
                                "aborted_before_onset",
                                stimulus_index,
                            )
                        )
                        output.flush()
                        aborted = True
                        break

                    actual_onset = display.present_grating(event.orientation_deg)
                    if actual_onset is None:
                        writer.writerow(
                            _event_row(
                                event,
                                target_onset,
                                None,
                                None,
                                block_start,
                                session_start_monotonic,
                                session_start_wall,
                                "aborted_during_stimulus",
                                stimulus_index,
                            )
                        )
                        output.flush()
                        aborted = True
                        break

                    offset_target = actual_onset + config.stimulus_duration_s
                    try:
                        stimulus_completed = display.wait_until(offset_target)
                    except (Exception, KeyboardInterrupt) as error:
                        display.show_gray()
                        writer.writerow(_event_row(
                            event, target_onset, actual_onset, time.monotonic(), block_start,
                            session_start_monotonic, session_start_wall,
                            'aborted_during_stimulus' if isinstance(error, KeyboardInterrupt)
                            else 'failed_during_stimulus', stimulus_index,
                        ))
                        output.flush()
                        raise
                    if not stimulus_completed:
                        display.show_gray()
                        actual_offset = time.monotonic()
                        writer.writerow(
                            _event_row(
                                event,
                                target_onset,
                                actual_onset,
                                actual_offset,
                                block_start,
                                session_start_monotonic,
                                session_start_wall,
                                "aborted_during_stimulus",
                                stimulus_index,
                            )
                        )
                        output.flush()
                        aborted = True
                        break

                    display.show_gray()
                    actual_offset = time.monotonic()
                    writer.writerow(
                        _event_row(
                            event,
                            target_onset,
                            actual_onset,
                            actual_offset,
                            block_start,
                            session_start_monotonic,
                            session_start_wall,
                            "complete",
                            stimulus_index,
                        )
                    )
                    output.flush()
                    previous_actual_onset = actual_onset

                if aborted:
                    break

                if block_number < config.block_count:
                    block_end = (
                        previous_actual_onset + onset_interval
                        if previous_actual_onset is not None
                        else time.monotonic()
                    )
                    if not display.wait_until(block_end):
                        aborted = True
                        break
                    next_block_start = block_end + config.inter_block_interval_s

    except KeyboardInterrupt:
        aborted = True
    except Exception as error:
        failed = True
        metadata['error'] = str(error)
        print('MMN failed: {}'.format(error), flush=True)
    finally:
        recording_errors = []
        try:
            display.show_gray()
        except Exception as error:
            recording_errors.append('Could not restore gray background: {}'.format(error))
        try:
            recording_errors.extend(recordings.stop())
        except (Exception, KeyboardInterrupt) as error:
            recording_errors.append('Recording shutdown interrupted or failed: {}'.format(error))
        finally:
            try:
                display.close()
            except Exception as error:
                recording_errors.append('Display shutdown failed: {}'.format(error))
        if recording_errors:
            failed = True
            metadata['recording_errors'] = recording_errors
            print('\n'.join(recording_errors), flush=True)

    metadata["status"] = "failed" if failed else "aborted" if aborted else "complete"
    metadata["finished_at"] = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    metadata["event_log"] = str(csv_path)
    metadata["session_elapsed_s"] = round(
        time.monotonic() - session_start_monotonic, 3
    )
    _write_metadata(metadata_path, metadata)
    print(f"Event log: {csv_path}")
    print(f"Session metadata: {metadata_path}")
    return 1 if failed else 130 if aborted else 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Present passive visual MMN oddball stimuli without optogenetic outputs"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override session_info.py's directory for CSV/JSON session logs",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible standard-count ordering",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Use a 5-second spontaneous period, one trial each of oddball A/B, and one control stimulus per angle",
    )
    parser.add_argument(
        "--backend",
        choices=("rpg", "pygame"),
        default=None,
        help="Override session_info.py's display backend (rpg uses the Pi framebuffer)",
    )
    parser.add_argument(
        "--display",
        type=int,
        default=None,
        help="Override the zero-based SDL display index for the pygame backend",
    )
    parser.add_argument(
        '--no-recording',
        action='store_true',
        help='Disable camera/treadmill acquisition for a visual-only check',
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Select pygame and open a window for a desktop check",
    )
    args = parser.parse_args()
    if args.backend == 'rpg' and (args.windowed or args.display is not None):
        parser.error("--windowed and --display apply to --backend pygame")
    if args.display is not None and args.display < 0:
        parser.error("--display cannot be negative")
    return args


def _config_from_session_info(session_info: Dict[str, object]) -> MMNConfig:
    """Convert editable settings to validated protocol parameters in seconds/degrees."""
    parameters = {
        field.name: session_info[field.name]
        for field in fields(MMNConfig)
        if field.name in session_info
    }
    parameters['stimulus_duration_s'] = session_info['grating_duration']
    parameters['inter_stimulus_interval_s'] = session_info['inter_grating_interval']
    return MMNConfig(**parameters)


def main() -> int:
    args = _parse_args()
    session_info = make_session_info()
    if session_info['task_config'] != 'mmn':
        raise ValueError("Set task_config to 'mmn' in session_info.py")
    if args.backend is not None:
        session_info['visual_backend'] = args.backend
    if args.windowed or args.display is not None:
        session_info['visual_backend'] = 'pygame'
    if args.display is not None:
        session_info['display_index'] = args.display
    if args.no_recording:
        session_info['camera_enabled'] = False
        session_info['treadmill'] = False
    windowed = args.windowed or session_info['windowed']
    config = _config_from_session_info(session_info)
    if args.test_mode:
        config = replace(
            config,
            block_count=3,
            trials_per_block=1,
            standard_count_options=(4,),
            inter_block_interval_s=5.0,
            control_trials_per_block=len(config.control_orientations_deg),
            spontaneous_duration_s=5.0,
        )
    if args.seed is not None:
        config = replace(config, random_seed=args.seed)

    session_info.setdefault('camera_preview_before_recording', True)
    if session_info.get('camera_enabled', False) and session_info['camera_preview_before_recording']:
        # The adjustment phase targets this rig's camera monitor by default;
        # an explicitly configured Qt desktop preview is also supported.
        session_info['camera_nodes'] = [dict(node, preview_backend=node.get('preview_backend', 'drm'))
                                        for node in session_info.get('camera_nodes', [])]
        preview_status = run_preview(session_info, continue_to_recording=True)
        if preview_status != 0:
            return preview_status
        print('Camera adjustment complete. Preparing the display and starting recording. Ctrl+C now stops the session.', flush=True)

    output_root = (args.output_dir or Path(session_info['output_dir'])).expanduser()
    output_dir = create_session_directory(output_root, session_info['mouse_name'])
    session_info['output_root'] = str(output_root)
    session_info['session_name'] = output_dir.name
    print(
        f"Mouse: {session_info['mouse_name']}; backend: {session_info['visual_backend']}; "
        f"orientations: {config.orientations_deg}; "
        f"grating/gray: {config.stimulus_duration_s}/{config.inter_stimulus_interval_s} s"
    )
    print(f"Block order: {' -> '.join(config.block_types)}")
    print('Camera recording: {}; treadmill recording: {}'.format(
        session_info.get('camera_enabled', False), session_info.get('treadmill', False)))
    print('Session directory: {}'.format(output_dir), flush=True)
    return run_protocol(config, output_dir, windowed=windowed, session_info=session_info)


if __name__ == "__main__":
    raise SystemExit(main())
