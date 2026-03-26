"""Tiny helper to play the WAV files under essential/sound."""

from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    import pygame
except ModuleNotFoundError:
    pygame = None


SOUND_DIR = Path(__file__).resolve().parents[1] / "essential" / "sound"


def _enumerate_sounds() -> dict[str, Path]:
    """Return a name->path map for the directory so callers can validate user input."""

    if not SOUND_DIR.exists():
        raise SystemExit(f"Sound directory {SOUND_DIR} is missing")
    return {path.name: path for path in sorted(SOUND_DIR.iterdir()) if path.is_file()}


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("duration must be > 0")
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
        "--duration",
        type=_positive_float,
        default=None,
        help="Play for this many seconds (overrides --loops)",
    )
    parser.add_argument(
        "--loops",
        type=_positive_int,
        default=1,
        help="How many times to play the file (default 1, ignored if --duration is set)",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "pygame", "aplay"),
        default="aplay",
        help="Preferred playback backend (default: aplay)",
    )
    parser.add_argument(
        "--device",
        default="plughw:2,0",
        help="ALSA device to pass to aplay (default: plughw:2,0); ignored for pygame",
    )
    return parser.parse_args()


def _play_sound(path: Path, loops: int, duration: float | None, backend: str, device: str | None) -> None:
    """Load and play the selected file, waiting until playback completes."""

    if backend in ("aplay", "auto") and shutil.which("aplay"):
        _play_with_aplay(path, loops, duration, device)
        return

    if pygame is None:
        raise SystemExit(
            "pygame is not installed; install it or run with --backend aplay"
        )
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(str(path))
        # pygame counts interrupted plays as loops, so we subtract one to match the CLI arg.
        pygame.mixer.music.play(loops=max(loops - 1, 0))
        
        if duration is not None:
            start_time = time.time()
            while pygame.mixer.music.get_busy() and (time.time() - start_time) < duration:
                pygame.time.wait(100)
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        else:
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
    finally:
        pygame.mixer.quit()


def _play_with_aplay(path: Path, loops: int, duration: float | None, device: str | None) -> None:
    """Use ALSA aplay utility to play a file when SDL audio is not configured."""

    aplay_exec = shutil.which("aplay")
    if not aplay_exec:
        raise SystemExit("aplay is required for the ALSA backend but was not found")

    base_cmd = [aplay_exec]
    if device:
        base_cmd += ["-D", device]

    if duration is not None:
        # Play for duration seconds by running aplay in background and timing out
        start_time = time.time()
        while (time.time() - start_time) < duration:
            proc = subprocess.Popen(base_cmd + [str(path)])
            # Calculate remaining time
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            if remaining > 0:
                try:
                    proc.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    break
    else:
        for _ in range(loops):
            subprocess.run(base_cmd + [str(path)], check=True)


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

    if args.duration is not None:
        print(f"Playing {path.name} for {args.duration}s")
        _play_sound(path, args.loops, args.duration, args.backend, args.device)
    else:
        print(f"Playing {path.name} ({args.loops} loop(s) requested)")
        _play_sound(path, args.loops, None, args.backend, args.device)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Playback interrupted")
