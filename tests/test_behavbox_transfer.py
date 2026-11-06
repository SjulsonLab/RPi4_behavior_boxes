"""Test the real BehavBox transfer orchestration without initializing hardware."""

import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def box_environment(monkeypatch, tmp_path):
    """Accept patch/path fixtures; return uninitialized BehavBox and transfer call state."""
    monkeypatch.setitem(sys.modules, "gpiozero", types.SimpleNamespace(PWMLED=object, LED=object, Button=object))
    monkeypatch.setitem(sys.modules, "icecream", types.SimpleNamespace(ic=print))
    monkeypatch.setitem(sys.modules, "essential.visual_stimuli.visualstim_concurrent", types.SimpleNamespace(VisualStimMultiprocess=object))
    for name in ("Treadmill", "ADS1x15"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "FlipperOutput", types.SimpleNamespace(FlipperOutput=object))
    monkeypatch.setitem(sys.modules, "base_classes", types.SimpleNamespace(Presenter=object, PumpBase=object, Box=object))
    path = Path(__file__).resolve().parents[1] / "essential" / "behavbox.py"
    specification = importlib.util.spec_from_file_location("behavbox_transfer_tests", path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    box = object.__new__(module.BehavBox)
    buffer_dir = tmp_path / "buffer"
    buffer_dir.mkdir()
    box.session_info = {
        "buffer_dir": str(buffer_dir), "session_name": "session",
        "file_basename": str(buffer_dir / "session" / "session"),
        "output_dir": str(buffer_dir / "session"),
        "external_storage": str(tmp_path / "external"),
        "external_storage_dir": str(tmp_path / "external" / "session"),
    }
    box.recording_camera_nodes = [
        {"camera_id": "cam0", "ssh_user": "pi", "host": "camera0"},
        {"camera_id": "cam1", "ssh_user": "pi", "host": "camera1"},
    ]
    monkeypatch.setattr(module.os.path, "ismount", mounted_storage)
    # The RED phase must never launch the old implementation's real SSH/rsync.
    monkeypatch.setattr(module.subprocess, "run", failed_old_transfer)
    monkeypatch.setattr(module.time, "sleep", skip_retry_delay)
    return box, module


def mounted_storage(path):
    """Accept filesystem path; simulate the configured external mount being present."""
    return True


def failed_old_transfer(arguments, **options):
    """Accept argv/options; simulate failure without contacting a real camera."""
    return subprocess.CompletedProcess(arguments, 12, stdout="", stderr="simulated transfer failure")


def skip_retry_delay(seconds):
    """Accept a delay in seconds; return immediately during orchestration tests."""
    return None


def test_camera_failure_does_not_block_other_camera_or_behavior(box_environment, monkeypatch, capsys):
    """Accept fixtures; all three sources are attempted and overall failure is explicit."""
    box, module = box_environment
    calls = []

    def transfer_source(**arguments):
        """Accept transfer keyword data; fail cam0 and succeed for other sources."""
        calls.append(arguments)
        return arguments.get("ssh_target") != "pi@camera0"

    monkeypatch.setattr(module, "transfer_files", transfer_source, raising=False)
    assert box.transfer_files_to_external_storage() is False
    assert len(calls) == 3
    assert [call.get("ssh_target") for call in calls] == ["pi@camera0", "pi@camera1", None]
    assert all(call["source"] == box.session_info["output_dir"] for call in calls)
    assert all(Path(call["log_path"]).parent == Path(box.session_info["buffer_dir"]) for call in calls)
    output = capsys.readouterr().out
    assert "MANUAL RECOVERY REQUIRED" in output
    assert "pi@camera0:" in output
    assert box.session_info["external_storage_dir"] in output
    assert "rsync finished!" not in output


def test_all_sources_success_is_required_for_success_message(box_environment, monkeypatch, capsys):
    """Accept fixtures; successful selected sources yield True and overall success."""
    box, module = box_environment
    monkeypatch.setattr(module, "transfer_files", mounted_storage_transfer, raising=False)
    assert box.transfer_files_to_external_storage() is True
    assert "rsync finished!" in capsys.readouterr().out


def mounted_storage_transfer(**arguments):
    """Accept explicit transfer keyword data; simulate one successful source."""
    return True


def test_missing_mount_keeps_sources_and_does_not_create_destination(box_environment, monkeypatch, capsys):
    """Accept fixtures; missing mount prevents launches and identifies every source."""
    box, module = box_environment
    calls = []

    def no_mount(path):
        """Accept path; simulate an absent mount."""
        return False

    def unexpected_transfer(**arguments):
        """Accept transfer data; record an unexpected invocation."""
        calls.append(arguments)

    monkeypatch.setattr(module.os.path, "ismount", no_mount)
    monkeypatch.setattr(module, "transfer_files", unexpected_transfer, raising=False)
    assert box.transfer_files_to_external_storage() is False
    assert calls == []
    assert not Path(box.session_info["external_storage_dir"]).exists()
    output = capsys.readouterr().out
    for location in ("pi@camera0:", "pi@camera1:", box.session_info["output_dir"], box.session_info["external_storage_dir"]):
        assert location in output


def test_cancelled_transfer_stops_remaining_sources_and_lists_their_locations(box_environment, monkeypatch, capsys):
    """Accept fixtures; cancellation returns False and identifies unattempted sources."""
    box, module = box_environment
    calls = []

    def cancel_transfer(**arguments):
        """Accept transfer data; simulate a user interrupt during the first camera."""
        calls.append(arguments)
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "transfer_files", cancel_transfer, raising=False)
    assert box.transfer_files_to_external_storage() is False
    assert len(calls) == 1
    output = capsys.readouterr().out
    assert "not attempted" in output.lower()
    assert "pi@camera1:" in output
    assert box.session_info["output_dir"] in output


def test_filesystem_failure_reports_locations_instead_of_raising(box_environment, monkeypatch, capsys, tmp_path):
    """Accept fixtures; an invalid destination parent returns failure with source paths."""
    box, module = box_environment
    blocker = tmp_path / "not_a_directory"
    blocker.write_text("keep this file")
    box.session_info["external_storage_dir"] = str(blocker / "session")
    assert box.transfer_files_to_external_storage() is False
    output = capsys.readouterr().out
    assert "MANUAL RECOVERY REQUIRED" in output
    assert "pi@camera0:" in output
    assert str(blocker / "session") in output
    assert blocker.read_text() == "keep this file"
