"""Display a short drifting-grating preview on the selected monitor."""

import argparse
from dataclasses import replace

from task_protocol.mmn_task.mmn_protocol import MMNConfig
from task_protocol.mmn_task.visual_stimulus import DriftingGratingDisplay


def _positive_seconds(value: str) -> float:
    seconds = float(value)
    if seconds <= 0:
        raise argparse.ArgumentTypeError("seconds must be greater than zero")
    return seconds


def _nonnegative_index(value: str) -> int:
    index = int(value)
    if index < 0:
        raise argparse.ArgumentTypeError("display index cannot be negative")
    return index


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show a short drifting-grating preview on a monitor"
    )
    parser.add_argument(
        "--display",
        type=_nonnegative_index,
        default=1,
        help="Zero-based SDL display index (default: 1, the second display)",
    )
    parser.add_argument(
        "--seconds",
        type=_positive_seconds,
        default=10.0,
        help="Preview duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Show the preview in a window instead of fullscreen",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = replace(MMNConfig(), grating_top_cm=0.0, grating_size_cm=20.0)
    display = DriftingGratingDisplay(
        config, windowed=args.windowed, display_index=args.display
    )
    try:
        print(
            "Showing a drifting grating on display {} for {} seconds.".format(
                args.display + 1, args.seconds
            )
        )
        display.preview_grating(45, args.seconds)
    finally:
        display.close()
    print("Grating preview finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
