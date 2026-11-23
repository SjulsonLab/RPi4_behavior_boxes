"""Check patch placement and color transitions without a physical monitor."""

from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('size', [(0, 4), (-1, 4), (4.5, 4), (81, 4), (4, 41), (4,)])
def test_patch_size_must_fit_the_display(size):
    from task_protocol.mmn_task.photodiode import bottom_left_patch_rect

    with pytest.raises(ValueError):
        bottom_left_patch_rect((80, 40), size)


@pytest.mark.parametrize('enabled', [True, False])
def test_pygame_patch_is_bottom_left_and_tracks_stimulus(monkeypatch, enabled):
    monkeypatch.setenv('SDL_VIDEODRIVER', 'dummy')
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    import pygame
    from task_protocol.mmn_task.mmn_protocol import MMNConfig
    from task_protocol.mmn_task.visual_stimulus import DriftingGratingDisplay

    monkeypatch.setattr(pygame.display, 'Info', lambda: SimpleNamespace(current_w=80, current_h=40))
    config = MMNConfig(grating_top_cm=0, grating_size_cm=1, pixels_per_cm=40)
    display = DriftingGratingDisplay(
        config, windowed=True, photodiode_patch_enabled=enabled,
        photodiode_patch_size_px=(8, 6),
    )
    try:
        assert display.screen.get_size() == (80, 40)
        assert display.display_settings['photodiode_patch_enabled'] is enabled
        assert display.screen.get_at((1, 1))[:3] == (128, 128, 128)
        if enabled:
            assert display.display_settings['photodiode_rect_px'] == [0, 34, 8, 6]
            assert display.screen.get_at((1, 39))[:3] == (255, 255, 255)
            for angle in (45, 135, 22.5):
                display._draw_grating(angle, 0)
                assert display.screen.get_at((1, 39))[:3] == (0, 0, 0)
            display.show_gray()
            assert display.screen.get_at((1, 39))[:3] == (255, 255, 255)
        else:
            assert display.display_settings['photodiode_rect_px'] is None
            assert display.screen.get_at((1, 39))[:3] == (128, 128, 128)
    finally:
        display.close()
