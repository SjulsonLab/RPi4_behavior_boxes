"""Check the Pi backend without opening a framebuffer or requiring rpg."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from task_protocol.mmn_task.mmn_protocol import MMNConfig


@pytest.fixture
def fake_rpg(monkeypatch):
    """Return an rpg stand-in that records builds, loads, and display calls."""
    calls = []

    def build_grating(filename, options):
        calls.append(("build", filename, options.copy()))
        Path(filename).write_bytes(b"grating")

    def build_gray(filename, options):
        calls.append(("build_gray", filename, options.copy()))
        Path(filename).write_bytes(b"gray")

    class Screen:
        def __init__(self, **kwargs):
            calls.append(("open", kwargs))
            self.gray_level = kwargs['background']

        def load_grating(self, filename):
            calls.append(("load", filename))
            return filename

        def display_grating(self, grating):
            if 'mmn_gray_' in str(grating):
                calls.append(('gray_patch', grating))
            else:
                calls.append(("present", grating))
            return SimpleNamespace(start_time=1, mean_interframe=16667)

        def display_greyscale(self, level):
            calls.append(("gray", level))

        def close(self):
            calls.append(("close",))

    module = SimpleNamespace(Screen=Screen, build_grating=build_grating, SINE=1)
    monkeypatch.setitem(sys.modules, "rpg", module)
    from task_protocol.mmn_task import rpg_stimulus
    monkeypatch.setattr(rpg_stimulus, "write_rpg_grating", build_grating)
    monkeypatch.setattr(rpg_stimulus, "write_rpg_gray", build_gray)
    return module, calls


def test_builds_and_preloads_all_eight_angles_including_fractional_angles(fake_rpg, tmp_path):
    from task_protocol.mmn_task.rpg_stimulus import RPGGratingDisplay

    _, calls = fake_rpg
    display = RPGGratingDisplay(MMNConfig(), tmp_path)
    builds = [call for call in calls if call[0] == "build"]
    assert {call[2]["angle"] for call in builds} == {22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180}
    assert len(builds) == 8
    for _, filename, options in builds:
        assert options["duration"] == 0.5
        assert options["temp_freq"] == 2.0
        assert options["spac_freq"] == 0.2
        assert options["resolution"] == (1280, 720)
        assert options["screen_width_degrees"] == 80.0
        assert options["refresh_rate_hz"] == 60
        assert "vertical" not in str(filename) and "horizontal" not in str(filename)
    assert len([call for call in calls if call[0] == "load"]) == 9
    assert ("gray", 40) in calls
    assert display.display_settings["spatial_frequency_cycles_per_degree"] == 0.2
    assert display.display_settings["photodiode_patch_enabled"] is True
    assert display.display_settings['photodiode_rect_px'] == [0, 680, 80, 40]
    assert all(call[2]['photodiode_rect_px'] == (0, 680, 80, 40) for call in builds)
    assert any(call[0] == 'gray_patch' for call in calls)
    display.close()


def test_cache_changes_when_stimulus_settings_change(fake_rpg, tmp_path):
    from task_protocol.mmn_task.rpg_stimulus import RPGGratingDisplay

    _, calls = fake_rpg
    for frequency in (0.2, 0.2, 0.1):
        display = RPGGratingDisplay(
            MMNConfig(), tmp_path, spatial_frequency_cycles_per_degree=frequency
        )
        display.close()
    assert len([call for call in calls if call[0] == "build"]) == 16


def test_onset_is_sampled_before_blocking_playback(fake_rpg, tmp_path, monkeypatch):
    from task_protocol.mmn_task import rpg_stimulus

    module, calls = fake_rpg
    clock = SimpleNamespace(now=10.0)

    def play(grating):
        if 'mmn_gray_' in str(grating):
            return SimpleNamespace(start_time=10)
        calls.append(("present", grating))
        clock.now += 0.5
        return SimpleNamespace(start_time=10)

    monkeypatch.setattr(module.Screen, "display_grating", lambda self, grating: play(grating))
    monkeypatch.setattr(rpg_stimulus, "time", SimpleNamespace(monotonic=lambda: clock.now))
    display = rpg_stimulus.RPGGratingDisplay(MMNConfig(), tmp_path)
    assert display.present_grating(135) == 10.0
    assert clock.now == 10.5
    assert "135" in [call for call in calls if call[0] == "present"][0][1]
    display.close()


def test_loading_failure_closes_framebuffer(fake_rpg, tmp_path, monkeypatch):
    from task_protocol.mmn_task.rpg_stimulus import RPGGratingDisplay

    module, calls = fake_rpg

    def fail_load(self, filename):
        raise OSError("load failed")

    monkeypatch.setattr(module.Screen, "load_grating", fail_load)
    with pytest.raises(OSError, match="load failed"):
        RPGGratingDisplay(MMNConfig(), tmp_path)
    assert calls[-1] == ("close",)


def test_interrupted_playback_stops_schedule(fake_rpg, tmp_path, monkeypatch):
    from task_protocol.mmn_task.rpg_stimulus import RPGGratingDisplay

    module, calls = fake_rpg
    monkeypatch.setattr(
        module.Screen, "display_grating",
        lambda self, grating: SimpleNamespace(start_time=0) if 'mmn_gray_' in str(grating) else None,
    )
    display = RPGGratingDisplay(MMNConfig(), tmp_path)
    assert display.present_grating(45) is None
    assert display.wait_until(0.0) is False
    display.close()
    display.close()
    assert len([call for call in calls if call[0] == "close"]) == 1


def test_patch_can_be_disabled_and_changes_cache_files(fake_rpg, tmp_path):
    from task_protocol.mmn_task.rpg_stimulus import RPGGratingDisplay

    _, calls = fake_rpg
    for enabled, size in [(True, (8, 6)), (True, (8, 6)), (False, (8, 6)), (True, (4, 4))]:
        display = RPGGratingDisplay(
            MMNConfig(), tmp_path, resolution=(80, 40),
            photodiode_patch_enabled=enabled, photodiode_patch_size_px=size,
        )
        assert display.display_settings['photodiode_patch_enabled'] is enabled
        if not enabled:
            assert display.display_settings['photodiode_rect_px'] is None
            display.show_gray()
            assert calls[-1] == ('gray', 40)
        display.close()
    assert len([call for call in calls if call[0] == 'build']) == 24
    assert len([call for call in calls if call[0] == 'build_gray']) == 2


@pytest.mark.parametrize('frame_type', ['gray', 'grating'])
@pytest.mark.parametrize('build_fails', [False, True])
def test_cache_cleanup_supports_legacy_python_unlink(monkeypatch, tmp_path, frame_type, build_fails):
    """Simulate Python 3.7, whose Path.unlink accepts no missing_ok keyword."""
    from task_protocol.mmn_task import rpg_stimulus

    original_unlink = Path.unlink

    def legacy_unlink(self):
        return original_unlink(self)

    def build(path, options):
        path.write_bytes(b'generated frame')
        if build_fails:
            raise OSError('grating generation failed')

    monkeypatch.setattr(Path, 'unlink', legacy_unlink)
    monkeypatch.setattr(rpg_stimulus, 'write_rpg_gray', build)
    monkeypatch.setattr(rpg_stimulus, 'write_rpg_grating', build)
    path = tmp_path / 'cached.dat'
    if build_fails:
        with pytest.raises(OSError, match='grating generation failed'):
            rpg_stimulus.RPGGratingDisplay._build_grating(path, {'frame_type': frame_type})
        assert list(tmp_path.iterdir()) == []
    else:
        rpg_stimulus.RPGGratingDisplay._build_grating(path, {'frame_type': frame_type})
        assert path.read_bytes() == b'generated frame'
        assert list(tmp_path.iterdir()) == [path]
