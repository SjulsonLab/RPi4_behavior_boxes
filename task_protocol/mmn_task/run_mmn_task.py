#!/usr/bin/env python3
"""Run the passive visual MMN protocol without optogenetic outputs."""

import argparse
import csv
import json
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from task_protocol.mmn_task.mmn_protocol import MMNConfig, StimulusEvent, build_schedule
from task_protocol.mmn_task.visual_stimulus import DriftingGratingDisplay


def _write_metadata(path: Path, metadata: Dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as output:
        json.dump(metadata, output, indent=2)
        output.write("\n")


def _event_row(
    event: StimulusEvent,
    target_onset: float,
    actual_onset: Optional[float],
    actual_offset: Optional[float],
    block_start: float,
    session_start_monotonic: float,
    session_wall_start: float,
    status: str,
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
        "block": event.block_number,
        "trial": event.trial_number,
        "sequence_position": event.sequence_position,
        "stimulus_type": event.stimulus_type,
        "orientation_deg": event.orientation_deg,
        "standards_before_deviant": event.standards_before_deviant,
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
) -> int:
    schedule = build_schedule(config)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"mmn_events_{session_id}.csv"
    metadata_path = output_dir / f"mmn_metadata_{session_id}.json"
    metadata: Dict[str, object] = {
        "session_id": session_id,
        "status": "starting",
        "opto_enabled": False,
        "visual_backend": "pygame_procedural_drifting_grating",
        "blocks": config.block_count,
        "trials_per_block": config.trials_per_block,
        "stimuli_per_trial": config.stimuli_per_trial,
        "standard_count_options": list(config.standard_count_options),
        "orientations_deg": list(config.orientations_deg),
        "stimulus_duration_s": config.stimulus_duration_s,
        "inter_stimulus_interval_s": config.inter_stimulus_interval_s,
        "inter_block_interval_s": config.inter_block_interval_s,
        "spatial_frequency_cycles_per_cm": config.spatial_frequency_cycles_per_cm,
        "temporal_frequency_hz": config.temporal_frequency_hz,
        "pixels_per_cm": config.pixels_per_cm,
        "grating_size_cm": config.grating_size_cm,
        "grating_top_cm": config.grating_top_cm,
        "random_seed": config.random_seed,
        "windowed": windowed,
    }
    header = [
        "block",
        "trial",
        "sequence_position",
        "stimulus_type",
        "orientation_deg",
        "standards_before_deviant",
        "expected_onset_s",
        "actual_onset_s",
        "onset_lateness_s",
        "actual_duration_s",
        "onset_wall_time",
        "opto_enabled",
        "status",
    ]

    aborted = False
    display = DriftingGratingDisplay(config, windowed=windowed)
    metadata["display"] = display.display_settings
    metadata["status"] = "running"
    session_start_monotonic = time.monotonic()
    session_start_wall = time.time()
    _write_metadata(metadata_path, metadata)
    try:
        metadata["started_at"] = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
        _write_metadata(metadata_path, metadata)

        with csv_path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=header)
            writer.writeheader()
            output.flush()

            block_events = config.trials_per_block * config.stimuli_per_trial
            onset_interval = config.stimulus_onset_interval_s
            next_block_start = time.monotonic()

            for block_number in range(1, config.block_count + 1):
                if not display.wait_until(next_block_start):
                    aborted = True
                    break

                block_events_list = schedule[
                    (block_number - 1) * block_events : block_number * block_events
                ]
                block_start = time.monotonic()
                previous_actual_onset: Optional[float] = None

                for event_index, event in enumerate(block_events_list):
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
                            )
                        )
                        output.flush()
                        aborted = True
                        break

                    offset_target = actual_onset + config.stimulus_duration_s
                    if not display.wait_until(offset_target):
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
    finally:
        display.close()

    metadata["status"] = "aborted" if aborted else "complete"
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
    return 130 if aborted else 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Present passive visual MMN oddball stimuli without optogenetic outputs"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "experimental_data" / "mmn",
        help="Directory for CSV event logs and JSON session metadata",
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
        help="Present one 8-stimulus trial with four standards in one block",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Open a window rather than taking over the full display",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = MMNConfig()
    if args.test_mode:
        config = replace(
            config,
            block_count=1,
            trials_per_block=1,
            standard_count_options=(4,),
            inter_block_interval_s=5.0,
        )
    if args.seed is not None:
        config = replace(config, random_seed=args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    return run_protocol(config, args.output_dir, windowed=args.windowed)


if __name__ == "__main__":
    raise SystemExit(main())
