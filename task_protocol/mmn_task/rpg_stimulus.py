"""Present precomputed MMN gratings through the Pi backend used by matt-behavior."""

import hashlib
import json
import math
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from task_protocol.mmn_task.mmn_protocol import MMNConfig
from task_protocol.mmn_task.photodiode import bottom_left_patch_rect
from task_protocol.mmn_task.rpg_grating import write_rpg_grating, write_rpg_gray


class RPGGratingDisplay:
    """Use one framebuffer and preload all planned angles before a session starts."""

    def __init__(
        self,
        config: MMNConfig,
        gratings_dir: Path,
        spatial_frequency_cycles_per_degree: float = 0.2,
        gray_level: int = 40,
        resolution: Tuple[int, int] = (1280, 720),
        screen_width_degrees: float = 80.0,
        photodiode_patch_enabled: bool = True,
        photodiode_patch_size_px: Tuple[int, int] = (80, 40),
    ) -> None:
        """Load config and cached gratings; resolution is (width, height) in pixels.

        Spatial frequency is cycles per visual degree; screen_width_degrees
        specifies the screen's visual angle. Gray level is 0–255. Returns None.
        An enabled patch uses size_px=(width, height) framebuffer pixels at the
        bottom-left, white during gray and black during grating presentation.
        """
        if not math.isfinite(spatial_frequency_cycles_per_degree) or spatial_frequency_cycles_per_degree <= 0:
            raise ValueError("spatial_frequency_cycles_per_degree must be positive and finite")
        if not isinstance(gray_level, int) or not 0 <= gray_level <= 255:
            raise ValueError("gray_level must be an integer from 0 to 255")
        if len(resolution) != 2 or any(not isinstance(n, int) or n <= 0 for n in resolution):
            raise ValueError("grating_resolution must contain positive integer width and height")
        if not math.isfinite(screen_width_degrees) or screen_width_degrees <= 0:
            raise ValueError("screen_width_degrees must be positive and finite")
        if not isinstance(photodiode_patch_enabled, bool):
            raise ValueError("photodiode_patch_enabled must be True or False")
        self._photodiode_rect = (
            bottom_left_patch_rect(resolution, photodiode_patch_size_px)
            if photodiode_patch_enabled else None
        )
        try:
            import rpg
        except ImportError as error:
            raise RuntimeError(
                "The rpg backend requires the Raspberry Pi environment used by "
                "matt-behavior/main.py. For a desktop check, use --backend pygame."
            ) from error

        self.config = config
        self.gray_level = gray_level
        self._aborted = False
        self._screen = None
        self._gray_grating = None
        self._gratings = {}
        self._grating_files = {}
        cache_dir = Path(gratings_dir).expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.display_settings = {
            "backend": "rpg_precomputed_drifting_grating",
            "screen_width_px": resolution[0],
            "screen_height_px": resolution[1],
            "gray_level": gray_level,
            "spatial_frequency_cycles_per_degree": spatial_frequency_cycles_per_degree,
            "temporal_frequency_hz_requested": config.temporal_frequency_hz,
            "screen_width_degrees": screen_width_degrees,
            "refresh_rate_hz": config.refresh_rate_hz,
            "grating_generator": "mmn_numpy_rgb565_v2",
            "grating_extent": "full_frame",
            "photodiode_patch_enabled": photodiode_patch_enabled,
            "photodiode_rect_px": list(self._photodiode_rect) if self._photodiode_rect else None,
            "photodiode_gray_level": 255 if photodiode_patch_enabled else None,
            "photodiode_stimulus_level": 0 if photodiode_patch_enabled else None,
            "onset_time_reference": "software_call_before_blocking_rpg_display",
            "grating_files": self._grating_files,
        }

        # Screen and files must have identical resolution and color depth.
        self._screen = rpg.Screen(resolution=resolution, background=gray_level, colormode=16)
        try:
            # Display ordinary gray while preparing the cached background frame.
            self.show_gray()
            if self._photodiode_rect is not None:
                gray_options = {
                    "frame_type": "gray",
                    "resolution": resolution,
                    "refresh_rate_hz": config.refresh_rate_hz,
                    "gray_level": gray_level,
                    "photodiode_rect_px": self._photodiode_rect,
                    "generator": "mmn_numpy_rgb565_v2",
                }
                self._gray_grating, gray_path = self._load_cached_grating(
                    cache_dir, 'mmn_gray', gray_options
                )
                self.display_settings['gray_frame_file'] = gray_path
                self.show_gray()
            for orientation in config.grating_orientations_deg:
                options = {
                    "duration": config.stimulus_duration_s,
                    "angle": orientation,
                    "spac_freq": spatial_frequency_cycles_per_degree,
                    "temp_freq": config.temporal_frequency_hz,
                    "resolution": resolution,
                    "screen_width_degrees": screen_width_degrees,
                    "refresh_rate_hz": config.refresh_rate_hz,
                    "photodiode_rect_px": self._photodiode_rect,
                    "generator": "mmn_numpy_rgb565_v2",
                }
                self._gratings[orientation], path = self._load_cached_grating(
                    cache_dir, f'mmn_{orientation}deg', options
                )
                self._grating_files[str(orientation)] = path
        except BaseException:
            self.close()
            raise

    def present_grating(self, orientation_deg: float) -> Optional[float]:
        """Play one preloaded angle in degrees; return software onset in monotonic seconds.

        Playback blocks for the duration encoded in the file. The timestamp is
        sampled before the call; rpg's Unix start_time has only second precision.
        Return None if playback reports an interruption.
        """
        if self._aborted:
            return None
        onset = time.monotonic()
        performance = self._screen.display_grating(self._gratings[orientation_deg])
        if performance is None:
            self._aborted = True
            self.show_gray()
            return None
        return onset

    def wait_until(self, deadline: float) -> bool:
        """Wait for a monotonic deadline in seconds; return False after interruption.

        Ctrl+C raises KeyboardInterrupt, handled by the session runner.
        """
        while not self._aborted:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(remaining, 0.005))
        return False

    def show_gray(self) -> None:
        """Show gray with a white patch when enabled; return None after refresh."""
        if self._screen is not None:
            if self._gray_grating is not None:
                self._screen.display_grating(self._gray_grating)
            else:
                self._screen.display_greyscale(self.gray_level)

    def close(self) -> None:
        """Restore gray and release the framebuffer once; return None."""
        if self._screen is not None:
            screen = self._screen
            self._screen = None
            try:
                if self._gray_grating is not None:
                    screen.display_grating(self._gray_grating)
                else:
                    screen.display_greyscale(self.gray_level)
            finally:
                screen.close()

    def _load_cached_grating(self, cache_dir: Path, name: str, options: dict):
        """Return (loaded grating, filename str) for settings cached under cache_dir."""
        digest = hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()[:16]
        path = cache_dir / f'{name}_{digest}.dat'
        if not path.is_file():
            self._build_grating(path, options)
        return self._screen.load_grating(str(path)), str(path)

    @staticmethod
    def _build_grating(path: Path, options: dict) -> None:
        """Build options into a cache Path atomically; return None (no partial cache)."""
        print(f"Building MMN grating: {path.name}")
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".dat", delete=False) as output:
            temporary_path = Path(output.name)
        try:
            if options.get('frame_type') == 'gray':
                write_rpg_gray(temporary_path, options)
            else:
                write_rpg_grating(temporary_path, options)
            temporary_path.replace(path)
        finally:
            # The rename removes the temporary filename on success. Python 3.7
            # has no unlink(missing_ok=...), so ignore only an absent file.
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
