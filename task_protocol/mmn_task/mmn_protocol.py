"""MMN trial scheduling based on the referenced Psychtoolbox protocol."""

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class MMNConfig:
    block_count: int = 9
    trials_per_block: int = 96
    stimuli_per_trial: int = 8
    standard_count_options: Tuple[int, ...] = (4, 5, 6, 7)
    orientations_deg: Tuple[float, float] = (45, 135)
    stimulus_duration_s: float = 0.5
    inter_stimulus_interval_s: float = 0.7
    inter_block_interval_s: float = 120.0
    pixels_per_cm: float = 36.127
    grating_size_cm: float = 30.0
    grating_top_cm: float = 23.0
    spatial_frequency_cycles_per_cm: float = 0.2
    temporal_frequency_hz: float = 2.0
    refresh_rate_hz: int = 60
    random_seed: Optional[int] = None
    control_trials_per_block: int = 640
    control_orientations_deg: Tuple[float, ...] = (
        22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180
    )
    spontaneous_duration_s: float = 900.0
    block_order: Tuple[str, str, str] = ("oddball_A", "oddball_B", "control")

    def __post_init__(self) -> None:
        if self.block_count < 1:
            raise ValueError("block_count must be at least 1")
        supported_orders = (
            ("oddball_A", "oddball_B", "control"),
            ("control", "oddball_A", "oddball_B"),
        )
        if not isinstance(self.block_order, (tuple, list)) or tuple(self.block_order) not in supported_orders:
            raise ValueError(
                "block_order must be ('oddball_A', 'oddball_B', 'control') "
                "or ('control', 'oddball_A', 'oddball_B')"
            )
        if self.trials_per_block < 1:
            raise ValueError("trials_per_block must be at least 1")
        if self.stimuli_per_trial < 3:
            raise ValueError("stimuli_per_trial must be at least 3")
        if not self.standard_count_options:
            raise ValueError("standard_count_options must not be empty")
        if self.trials_per_block % len(self.standard_count_options) != 0:
            raise ValueError(
                "trials_per_block must be evenly divisible by the number "
                "of standard_count_options"
            )
        if len(set(self.standard_count_options)) != len(self.standard_count_options):
            raise ValueError("standard_count_options must not contain duplicates")
        if any(
            count < 1 or count > self.stimuli_per_trial - 1
            for count in self.standard_count_options
        ):
            raise ValueError("standard counts must leave room for a deviant")
        if (
            len(self.orientations_deg) != 2
            or self.orientations_deg[0] == self.orientations_deg[1]
        ):
            raise ValueError("orientations_deg must contain two distinct orientations")
        if not self.control_orientations_deg:
            raise ValueError("control_orientations_deg must not be empty")
        if len(set(self.control_orientations_deg)) != len(self.control_orientations_deg):
            raise ValueError("control_orientations_deg must not contain duplicates")
        if any(not math.isfinite(angle) for angle in (*self.orientations_deg, *self.control_orientations_deg)):
            raise ValueError("grating orientations must be finite")
        if self.control_trials_per_block < 1:
            raise ValueError("control_trials_per_block must be at least 1")
        if self.control_trials_per_block % len(self.control_orientations_deg) != 0:
            raise ValueError("control_trials_per_block must be divisible by the number of control orientations")
        if self.stimulus_duration_s <= 0:
            raise ValueError("stimulus_duration_s must be positive")
        if self.inter_stimulus_interval_s < 0:
            raise ValueError("inter_stimulus_interval_s cannot be negative")
        if self.inter_block_interval_s < 0:
            raise ValueError("inter_block_interval_s cannot be negative")
        if not math.isfinite(self.spontaneous_duration_s) or self.spontaneous_duration_s < 0:
            raise ValueError("spontaneous_duration_s must be finite and nonnegative")
        if self.pixels_per_cm <= 0 or self.grating_size_cm <= 0:
            raise ValueError("grating dimensions must be positive")
        if self.spatial_frequency_cycles_per_cm <= 0:
            raise ValueError("spatial_frequency_cycles_per_cm must be positive")
        if self.temporal_frequency_hz <= 0 or self.refresh_rate_hz <= 0:
            raise ValueError("grating and display rates must be positive")

    @property
    def stimulus_onset_interval_s(self) -> float:
        return self.stimulus_duration_s + self.inter_stimulus_interval_s

    @property
    def block_types(self) -> Tuple[str, ...]:
        """Return block_count labels by repeating the configured three-block order."""
        return tuple(
            self.block_order[index % len(self.block_order)]
            for index in range(self.block_count)
        )

    @property
    def grating_orientations_deg(self) -> Tuple[float, ...]:
        """Return all distinct angles in degrees needed by the planned blocks."""
        angles = tuple(self.orientations_deg)
        if "control" in self.block_types:
            angles += tuple(self.control_orientations_deg)
        return tuple(dict.fromkeys(angles))


@dataclass(frozen=True)
class StimulusEvent:
    block_number: int
    trial_number: int
    sequence_position: int
    stimulus_type: str
    orientation_deg: float
    standards_before_deviant: Optional[int]
    block_type: str = "oddball_A"


def build_schedule(config: MMNConfig) -> List[StimulusEvent]:
    """Return events in the selected block order, with balanced shuffled controls.

    Oddball trials contain stimuli_per_trial gratings; each control trial
    contains one grating. All event angles are degrees and trial indices are
    one-based within their block. Control events have no deviant count (None).
    """

    rng = random.Random(config.random_seed)
    events: List[StimulusEvent] = []
    trials_per_standard_count = (
        config.trials_per_block // len(config.standard_count_options)
    )

    for block_number, block_type in enumerate(config.block_types, start=1):
        if block_type == "control":
            presentations_per_angle = (
                config.control_trials_per_block // len(config.control_orientations_deg)
            )
            control_angles = [
                angle for angle in config.control_orientations_deg
                for _ in range(presentations_per_angle)
            ]
            rng.shuffle(control_angles)
            events.extend(
                StimulusEvent(
                    block_number=block_number,
                    trial_number=trial_number,
                    sequence_position=1,
                    stimulus_type="control",
                    orientation_deg=angle,
                    standards_before_deviant=None,
                    block_type=block_type,
                )
                for trial_number, angle in enumerate(control_angles, start=1)
            )
            continue

        standard_counts = [
            count
            for count in config.standard_count_options
            for _ in range(trials_per_standard_count)
        ]
        rng.shuffle(standard_counts)

        standard_orientation = config.orientations_deg[
            1 if block_type == "oddball_A" else 0
        ]
        deviant_orientation = config.orientations_deg[
            0 if block_type == "oddball_A" else 1
        ]

        for trial_number, standard_count in enumerate(standard_counts, start=1):
            for sequence_position in range(1, config.stimuli_per_trial + 1):
                is_deviant = sequence_position == standard_count + 1
                events.append(
                    StimulusEvent(
                        block_number=block_number,
                        trial_number=trial_number,
                        sequence_position=sequence_position,
                        stimulus_type="deviant" if is_deviant else "standard",
                        orientation_deg=(
                            deviant_orientation if is_deviant else standard_orientation
                        ),
                        standards_before_deviant=standard_count,
                        block_type=block_type,
                    )
                )

    return events
