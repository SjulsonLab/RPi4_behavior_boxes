"""Focused stop/transfer regressions; all camera and transfer commands are mocked."""

import importlib.util
from pathlib import Path
import shlex
import subprocess
import sys
import types

import pytest


@pytest.fixture
def capture_environment(monkeypatch):
    """Accept pytest's patch fixture; return (VideoCapture, command state), no units."""
    module_path = (
        Path(__file__).resolve().parents[1]
        / "essential/video_acquisition/VideoCapture.py"
    )
    monkeypatch.setitem(sys.modules, "colorama", types.SimpleNamespace(Fore=None, Style=None))
    monkeypatch.setitem(sys.modules, "scipy", types.ModuleType("scipy"))
    specification = importlib.util.spec_from_file_location("video_capture_stop_tests", module_path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    state = types.SimpleNamespace(shell_calls=[], run_calls=[], fail_rsync=None, fail_stage=None)

    def run_shell(command):
        """Accept a command str; record it and return an integer shell exit status."""
        state.shell_calls.append(command)
        if command.startswith("rsync"):
            count = sum(call.startswith("rsync") for call in state.shell_calls)
            if count == state.fail_rsync:
                return 256
        return 0

    def run_command(arguments, **options):
        """Accept argv list/options; return CompletedProcess or inject a transfer error."""
        state.run_calls.append(arguments)
        if (
            state.fail_stage == "copy" and arguments[0] == "scp"
            or state.fail_stage == "cleanup" and arguments[-1] == "rm -f ~/video/videolog.log"
        ):
            raise subprocess.CalledProcessError(1, arguments)
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(module.os, "system", run_shell)
    monkeypatch.setattr(module.subprocess, "run", run_command)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    capture = module.VideoCapture("camera-pi", "mouse", "/home/pi/video/session", "E:/videos")
    return capture, state


@pytest.mark.parametrize("directory", [
    "/home/pi/video/session 1", "/home/pi/video/mouse's session; $name", "~/video/session 1",
])
def test_windows_cleanup_keeps_directory_as_one_shell_argument(capture_environment, directory):
    """Accept fixture/path str; assert cleanup preserves literal names and Pi-side ~/ expansion."""
    capture, state = capture_environment
    capture.base_dir = directory
    capture.video_stop_windows()
    deletion = next(
        arguments[-1] for arguments in state.run_calls
        if arguments[0] == "ssh" and arguments[-1].startswith("rm -rf ")
    )
    expected = "$HOME/" + directory[2:] if directory.startswith("~/") else directory
    assert shlex.split(deletion) == ["rm", "-rf", expected]
    if directory.startswith("~/"):
        assert deletion.startswith('rm -rf "$HOME"/')


@pytest.mark.parametrize("stage", ["copy", "cleanup"])
def test_windows_failure_does_not_claim_sources_are_intact(capture_environment, capsys, stage):
    """Accept fixtures/stage str; assert copy and partial-cleanup errors produce an honest message."""
    capture, state = capture_environment
    state.fail_stage = stage
    capture.video_stop_windows()
    output = capsys.readouterr().out
    assert "Transfer or cleanup failed; check source files." in output
    assert "Source files were NOT deleted" not in output
    if stage == "copy":
        assert not any(arguments[-1].startswith("rm ") for arguments in state.run_calls)
    else:
        assert any(arguments[-1].startswith("rm -rf ") for arguments in state.run_calls)


def test_rsync_success_uses_only_two_remote_transfers(capture_environment, capsys):
    """Accept fixtures; assert successful transfers have remote sources and report completion."""
    capture, state = capture_environment
    capture.video_stop()
    transfers = [command for command in state.shell_calls if command.startswith("rsync")]
    assert len(transfers) == 2
    assert all("pi@camera-pi:" in command for command in transfers)
    assert "rsync finished!" in capsys.readouterr().out


@pytest.mark.parametrize("failed_transfer", [1, 2])
def test_rsync_failure_stops_without_success_message(capture_environment, capsys, failed_transfer):
    """Accept fixtures/transfer ordinal int; assert nonzero shell status stops remaining transfers."""
    capture, state = capture_environment
    state.fail_rsync = failed_transfer
    capture.video_stop()
    transfers = [command for command in state.shell_calls if command.startswith("rsync")]
    assert len(transfers) == failed_transfer
    output = capsys.readouterr().out
    assert "Video transfer failed." in output
    assert "rsync finished!" not in output
