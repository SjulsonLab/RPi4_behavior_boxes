"""Export the exact planned stimulus order and stable angle-based grating IDs."""

import csv
from pathlib import Path
from typing import Dict, Optional, Sequence

from task_protocol.mmn_task.mmn_protocol import StimulusEvent


GRATING_ANGLES_DEG = tuple(22.5 * index for index in range(1, 9))
_GRATING_ID_BY_ANGLE = {
    angle: index for index, angle in enumerate(GRATING_ANGLES_DEG, start=1)
}
STIMULUS_COLUMNS = (
    'stimulus_index', 'block', 'block_type', 'repetition', 'trial',
    'sequence_position', 'stimulus_type', 'orientation_deg', 'grating_id',
    'standards_before_deviant',
)


def stimulus_row(
    event: StimulusEvent, stimulus_index: Optional[int] = None
) -> Dict[str, object]:
    """Return CSV identity fields for one event and optional one-based session index.

    orientation_deg is in degrees; grating_id is 1–8 for angles 22.5:22.5:180.
    Custom angles outside that set retain their degrees with an empty ID.
    Control events have no standards_before_deviant value (None).
    """
    return {
        'stimulus_index': stimulus_index if stimulus_index is not None else '',
        'block': event.block_number,
        'block_type': event.block_type,
        'repetition': (event.block_number - 1) // 3 + 1,
        'trial': event.trial_number,
        'sequence_position': event.sequence_position,
        'stimulus_type': event.stimulus_type,
        'orientation_deg': event.orientation_deg,
        'grating_id': _GRATING_ID_BY_ANGLE.get(event.orientation_deg, ''),
        'standards_before_deviant': event.standards_before_deviant,
    }


def write_stimulus_sequence(path: Path, schedule: Sequence[StimulusEvent]) -> None:
    """Save schedule, in the supplied presentation order, to a new CSV; return None.

    path's parent directory must exist. One row represents one grating, with
    one-based stimulus_index spanning all blocks. This exports the already
    randomized schedule and never rebuilds or reshuffles it. Existing files
    are preserved by raising FileExistsError.
    """
    with path.open('x', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=STIMULUS_COLUMNS)
        writer.writeheader()
        writer.writerows(
            stimulus_row(event, index) for index, event in enumerate(schedule, start=1)
        )
