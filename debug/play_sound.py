"""Tiny helper to play the WAV files under essential/sound."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pygame


SOUND_DIR = Path(__file__).resolve().parents[1] / "essential" / "sound"


def _enumerate_sounds() -> dict[str, Path]:
    """Return a name->path map for the directory so callers can validate user input."""

    if not SOUND_DIR.exists():
        raise SystemExit(f"Sound directory {SOUND_DIR} is missing")
    return {path.name: path for path in sorted(SOUND_DIR.iterdir()) if path.is_file()}


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("loops must be at least 1")
    return parsed


def _parse_args(sound_map: dict[str, Path]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play a WAV file from essential/sound via pygame.mixer"
    )
    parser.add_argument(
        "sound",
        nargs="?",
        help="Name of the sound file in essential/sound",
        choices=list(sound_map),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print available sound files and exit",
    )
    parser.add_argument(
        "--loops",
        type=_positive_int,
        default=1,
        help="How many times to play the file (default 1)",
    )
    return parser.parse_args()


def _play_sound(path: Path, loops: int) -> None:
    """Load and play the selected file, waiting until playback completes."""

    pygame.mixer.init()
    try:
        pygame.mixer.music.load(str(path))
        # pygame counts interrupted plays as loops, so we subtract one to match the CLI arg.
        pygame.mixer.music.play(loops=max(loops - 1, 0))
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
    finally:
        pygame.mixer.quit()


def main() -> None:
    sound_map = _enumerate_sounds()
    args = _parse_args(sound_map)

    if args.list:
        for name in sound_map:
            print(name)
        return

    if not sound_map:
        raise SystemExit("No sounds found in essential/sound")

    choice = args.sound or next(iter(sound_map))
    path = sound_map.get(choice)
    assert path is not None  # mypy prefers this guard even though choices blocks missing keys.

    print(f"Playing {path.name} ({args.loops} loop(s) requested)")
    _play_sound(path, args.loops)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Playback interrupted")
