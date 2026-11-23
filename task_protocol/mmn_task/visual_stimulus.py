"""Procedural drifting-grating presentation using Pygame."""

import math
import time
from typing import Dict, Optional, Tuple

from task_protocol.mmn_task.mmn_protocol import MMNConfig
from task_protocol.mmn_task.photodiode import bottom_left_patch_rect


class DriftingGratingDisplay:
    def __init__(
        self, config: MMNConfig, windowed: bool = False, display_index: int = 0,
        photodiode_patch_enabled: bool = True,
        photodiode_patch_size_px: Tuple[int, int] = (80, 40),
    ) -> None:
        import numpy as np
        import pygame

        if display_index < 0:
            raise ValueError("display_index cannot be negative")
        if not isinstance(photodiode_patch_enabled, bool):
            raise ValueError("photodiode_patch_enabled must be True or False")

        self.config = config
        self.np = np
        self.pygame = pygame
        pygame.init()
        self.display_index = display_index

        if windowed:
            display_info = pygame.display.Info()
            width = min(display_info.current_w or 1280, 1280)
            height = min(display_info.current_h or 800, 800)
            self.screen = pygame.display.set_mode(
                (width, height), display=display_index
            )
        else:
            self.screen = pygame.display.set_mode(
                (0, 0), pygame.FULLSCREEN, display=display_index
            )

        pygame.display.set_caption("Visual MMN - display {}".format(display_index + 1))
        self.screen_width, self.screen_height = self.screen.get_size()
        self.clock = pygame.time.Clock()
        self.gray_level = 128
        self._pixels_per_cm = config.pixels_per_cm
        if windowed:
            fit_width = self.screen_width / config.grating_size_cm
            fit_height = self.screen_height / (
                config.grating_top_cm + config.grating_size_cm
            )
            self._pixels_per_cm *= min(
                1.0, fit_width / config.pixels_per_cm, fit_height / config.pixels_per_cm
            )
        self._grating_size_px = max(
            1, round(config.grating_size_cm * self._pixels_per_cm)
        )
        self._grating_rect = pygame.Rect(
            0,
            round(config.grating_top_cm * self._pixels_per_cm),
            self._grating_size_px,
            self._grating_size_px,
        )
        self._grating_surface = pygame.Surface(
            (self._grating_size_px, self._grating_size_px)
        )
        self._x_grid, self._y_grid = self._coordinate_grids(self._grating_size_px)
        self._phase_grids: Dict[float, object] = {}
        self._scratch = np.empty(
            (self._grating_size_px, self._grating_size_px), dtype=np.float32
        )
        self._frequency_cycles_per_pixel = (
            config.spatial_frequency_cycles_per_cm / self._pixels_per_cm
        )
        self._photodiode_rect = (
            pygame.Rect(bottom_left_patch_rect(
                (self.screen_width, self.screen_height), photodiode_patch_size_px
            )) if photodiode_patch_enabled else None
        )
        self._aborted = False
        self.display_settings = {
            "backend": "pygame_procedural_drifting_grating",
            "display_index": display_index,
            "screen_width_px": self.screen_width,
            "screen_height_px": self.screen_height,
            "pixels_per_cm_used": self._pixels_per_cm,
            "grating_rect_px": list(self._grating_rect),
            "photodiode_rect_px": list(self._photodiode_rect) if self._photodiode_rect else None,
            "photodiode_patch_enabled": photodiode_patch_enabled,
            "photodiode_gray_level": 255 if photodiode_patch_enabled else None,
            "photodiode_stimulus_level": 0 if photodiode_patch_enabled else None,
            "onset_time_reference": "software_time_after_first_pygame_flip",
        }
        self.show_gray()

    def _coordinate_grids(self, size: int):
        np = self.np
        coordinates = np.arange(size, dtype=np.float32) - (size - 1) / 2.0
        x_grid = np.broadcast_to(coordinates[:, None], (size, size))
        y_grid = np.broadcast_to(coordinates[None, :], (size, size))
        return x_grid, y_grid

    def _phase_grid(self, orientation_deg: float):
        if orientation_deg not in self._phase_grids:
            radians = math.radians(orientation_deg)
            projection = (
                self._x_grid * math.cos(radians)
                + self._y_grid * math.sin(radians)
            )
            self._phase_grids[orientation_deg] = (
                projection
                * (2.0 * math.pi * self._frequency_cycles_per_pixel)
            )
        return self._phase_grids[orientation_deg]

    def _process_events(self) -> bool:
        pygame = self.pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._aborted = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._aborted = True
        return not self._aborted

    def wait_until(self, deadline: float) -> bool:
        while True:
            if not self._process_events():
                return False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(remaining, 0.005))

    def show_gray(self) -> None:
        self.screen.fill((self.gray_level, self.gray_level, self.gray_level))
        if self._photodiode_rect is not None:
            self.pygame.draw.rect(self.screen, (255, 255, 255), self._photodiode_rect)
        self.pygame.display.flip()

    def _draw_grating(self, orientation_deg: float, elapsed_s: float) -> None:
        np = self.np
        phase = 2.0 * math.pi * self.config.temporal_frequency_hz * elapsed_s
        np.add(self._phase_grid(orientation_deg), phase, out=self._scratch)
        np.cos(self._scratch, out=self._scratch)
        np.multiply(self._scratch, 127.5, out=self._scratch)
        np.add(self._scratch, 127.5, out=self._scratch)
        np.clip(self._scratch, 0, 255, out=self._scratch)

        pixels = self.pygame.surfarray.pixels3d(self._grating_surface)
        np.copyto(pixels[:, :, 0], self._scratch, casting="unsafe")
        np.copyto(pixels[:, :, 1], self._scratch, casting="unsafe")
        np.copyto(pixels[:, :, 2], self._scratch, casting="unsafe")
        del pixels

        self.screen.fill((self.gray_level, self.gray_level, self.gray_level))
        self.screen.blit(self._grating_surface, self._grating_rect.topleft)
        if self._photodiode_rect is not None:
            self.pygame.draw.rect(self.screen, (0, 0, 0), self._photodiode_rect)

    def present_grating(self, orientation_deg: float) -> Optional[float]:
        actual_onset: Optional[float] = None

        while (
            actual_onset is None
            or time.monotonic() < actual_onset + self.config.stimulus_duration_s
        ):
            if not self._process_events():
                self.show_gray()
                return actual_onset

            elapsed_s = (
                0.0
                if actual_onset is None
                else time.monotonic() - actual_onset
            )
            self._draw_grating(orientation_deg, elapsed_s)
            self.pygame.display.flip()
            flip_time = time.monotonic()
            if actual_onset is None:
                actual_onset = flip_time
            self.clock.tick(self.config.refresh_rate_hz)

        return actual_onset

    def preview_grating(self, orientation_deg: float, duration_s: float) -> None:
        if duration_s <= 0:
            raise ValueError("duration_s must be positive")

        start = time.monotonic()
        deadline = start + duration_s
        try:
            while time.monotonic() < deadline and self._process_events():
                elapsed_s = time.monotonic() - start
                self._draw_grating(orientation_deg, elapsed_s)
                self.pygame.display.flip()
                self.clock.tick(self.config.refresh_rate_hz)
        finally:
            self.show_gray()

    def close(self) -> None:
        if self.pygame.get_init():
            self.show_gray()
            self.pygame.quit()
