"""MMN trial scheduling based on the referenced Psychtoolbox protocol."""

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class MMNConfig:
    block_count: int = 6
    trials_per_block: int = 96
    stimuli_per_trial: int = 8
    standard_count_options: Tuple[int, ...] = (4, 5, 6, 7)
    orientations_deg: Tuple[int, int] = (45, 135)
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

    def __post_init__(self) -> None:
        if self.block_count < 1:
            raise ValueError("block_count must be at least 1")
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
        if self.stimulus_duration_s <= 0:
            raise ValueError("stimulus_duration_s must be positive")
        if self.inter_stimulus_interval_s < 0:
            raise ValueError("inter_stimulus_interval_s cannot be negative")
        if self.inter_block_interval_s < 0:
            raise ValueError("inter_block_interval_s cannot be negative")
        if self.pixels_per_cm <= 0 or self.grating_size_cm <= 0:
            raise ValueError("grating dimensions must be positive")
        if self.spatial_frequency_cycles_per_cm <= 0:
            raise ValueError("spatial_frequency_cycles_per_cm must be positive")
        if self.temporal_frequency_hz <= 0 or self.refresh_rate_hz <= 0:
            raise ValueError("grating and display rates must be positive")

    @property
    def stimulus_onset_interval_s(self) -> float:
        return self.stimulus_duration_s + self.inter_stimulus_interval_s


@dataclass(frozen=True)
class StimulusEvent:
    block_number: int
    trial_number: int
    sequence_position: int
    stimulus_type: str
    orientation_deg: int
    standards_before_deviant: int


def build_schedule(config: MMNConfig) -> List[StimulusEvent]:
    """Build balanced trials, alternating the standard orientation by block."""

    rng = random.Random(config.random_seed)
    events: List[StimulusEvent] = []
    trials_per_standard_count = (
        config.trials_per_block // len(config.standard_count_options)
    )

    for block_number in range(1, config.block_count + 1):
        standard_counts = [
            count
            for count in config.standard_count_options
            for _ in range(trials_per_standard_count)
        ]
        rng.shuffle(standard_counts)

        standard_orientation = config.orientations_deg[
            1 if block_number % 2 == 1 else 0
        ]
        deviant_orientation = config.orientations_deg[
            0 if block_number % 2 == 1 else 1
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
                    )
                )

    return events
