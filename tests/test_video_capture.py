"""Regression tests for standalone camera control; no SSH or transfers are run."""

import builtins
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import types

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "essential/video_acquisition/VideoCapture.py"
)
PREVIEW_SCRIPT = "/home/pi/RPi4_behavior_boxes/video_acquisition/start_preview.py"
ACQUISITION_SCRIPT = "/home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.py"
REMOTE_DIRECTORY = "/home/pi/video/session 1; $name"
LOCAL_DIRECTORY = "E:/Video recordings/session 1"


@pytest.fixture
def camera_environment(monkeypatch):
    """Return a module and fake command state; inputs are pytest fixtures, no units."""
    colors = types.SimpleNamespace(CYAN="", RED="", GREEN="", YELLOW="")
    monkeypatch.setitem(
        sys.modules, "colorama",
        types.SimpleNamespace(Fore=colors, Style=types.SimpleNamespace(RESET_ALL="", BRIGHT="")),
    )
    monkeypatch.setitem(sys.modules, "scipy", types.ModuleType("scipy"))
    specification = importlib.util.spec_from_file_location("standalone_video_capture", MODULE_PATH)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    state = types.SimpleNamespace(
        calls=[], fail=None, resolved=REMOTE_DIRECTORY, interrupt_preview=False,
        ssh_version="OpenSSH_for_Windows_9.5p1, LibreSSL 3.8.2",
        entries=["mouse 1.h264", ".metadata", "sub directory"], created_directories=[],
    )

    def run_command(arguments, **options):
        """Accept argv list/options; return CompletedProcess or the injected failure."""
        state.calls.append((arguments, options))
        if arguments == ["ssh", "-V"]:
            return subprocess.CompletedProcess(arguments, 0, stdout="", stderr=state.ssh_version)
        if state.fail is not None and state.fail(arguments):
            raise subprocess.CalledProcessError(1, arguments)
        if arguments[0] == "ssh" and "json.dumps" in arguments[2]:
            return subprocess.CompletedProcess(arguments, 0, stdout=json.dumps(state.entries))
        if (
            state.interrupt_preview
            and arguments[0] == "ssh"
            and shlex.split(arguments[2]) in ([PREVIEW_SCRIPT], ["python3", PREVIEW_SCRIPT])
        ):
            raise KeyboardInterrupt
        return subprocess.CompletedProcess(arguments, 0, stdout=state.resolved + "\n")

    def reject_shell_command(command):
        """Accept a shell string; raise because unchecked os.system is forbidden here."""
        raise AssertionError("Use checked subprocess calls instead of os.system")

    monkeypatch.setattr(module.subprocess, "run", run_command)
    monkeypatch.setattr(module.os, "system", reject_shell_command)
    monkeypatch.setattr(
        module.os, "makedirs",
        lambda path, exist_ok: state.created_directories.append((path, exist_ok)),
    )
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(builtins, "input", lambda prompt: "")
    return module, state


@pytest.fixture
def camera(camera_environment):
    """Return VideoCapture for one Pi, one remote directory and one Windows destination."""
    module, _ = camera_environment
    return module.VideoCapture("camera-pi", "mouse 1; $name", REMOTE_DIRECTORY, LOCAL_DIRECTORY)


def remote_commands(state):
    """Accept fake state; return list[list[str]] of tokenized SSH commands, no units."""
    return [
        shlex.split(argv[2]) for argv, _ in state.calls
        if argv[0] == "ssh" and len(argv) == 3
    ]


def is_process_operation(arguments, operation):
    """Accept argv and mode strings; return bool identifying a remote process operation."""
    if arguments[0] != "ssh" or len(arguments) != 3:
        return False
    tokens = shlex.split(arguments[2])
    return len(tokens) == 6 and tokens[:2] == ["python3", "-c"] and tokens[4] == operation


@pytest.mark.parametrize("frame_rate", [15, 60])
def test_unsupported_frame_rate_fails_before_ssh(camera_environment, frame_rate):
    """Accept fixture/fps scalar; assert unsupported rates raise before side effects."""
    module, state = camera_environment
    with pytest.raises(ValueError, match="30"):
        module.VideoCapture("camera-pi", "mouse", REMOTE_DIRECTORY, LOCAL_DIRECTORY, frame_rate)
    assert state.calls == []


def test_start_preserves_paths_and_uses_downstream_default_camera_id(camera, camera_environment):
    """Accept fixtures; assert shell-sensitive paths stay intact and fps is not an ID."""
    _, state = camera_environment
    state.interrupt_preview = True
    camera.video_start()
    commands = remote_commands(state)
    assert ["python3", PREVIEW_SCRIPT] in commands
    launch = next(command for command in commands if command[0] == "nohup")
    assert launch[:5] == [
        "nohup", "python3", ACQUISITION_SCRIPT,
        REMOTE_DIRECTORY + "/mouse 1; $name", "</dev/null",
    ]
    mkdir = next(command for command in commands if command[0] == "mkdir")
    assert REMOTE_DIRECTORY in mkdir
    assert any(is_process_operation(argv, "check") for argv, _ in state.calls)
    assert all(options.get("check") is True for _, options in state.calls)
    assert not any("pkill" in command for command in commands)


def test_preview_interrupt_still_stops_only_the_preview(camera, camera_environment):
    """Accept fixtures; assert Ctrl-C triggers targeted cleanup with the correct path."""
    _, state = camera_environment
    state.interrupt_preview = True
    camera.video_preview_only()
    assert ["python3", PREVIEW_SCRIPT] in remote_commands(state)
    assert is_process_operation(state.calls[-1][0], "stop")
    assert shlex.split(state.calls[-1][0][2])[3] == PREVIEW_SCRIPT


@pytest.mark.parametrize("failure_stage", ["mkdir", "nohup", "check"])
def test_start_failure_reaches_caller(camera, camera_environment, failure_stage):
    """Accept fixtures/stage string; assert failed preparation/launch/check is propagated."""
    _, state = camera_environment
    state.fail = lambda argv: (
        argv[0] == "ssh" and (
            shlex.split(argv[2])[0] == failure_stage
            or (failure_stage == "check" and is_process_operation(argv, "check"))
        )
    )
    with pytest.raises(subprocess.CalledProcessError):
        camera.video_start()
    if failure_stage == "mkdir":
        assert not any(command[0] == "nohup" for command in remote_commands(state))


def test_windows_transfer_copies_whole_directory_then_quoted_cleanup(camera, camera_environment):
    """Accept fixtures; assert whole-directory copies precede safe source deletion."""
    _, state = camera_environment
    camera.video_stop_windows()
    transfers = [argv for argv, _ in state.calls if argv[0] == "scp"]
    assert transfers == [
        ["scp", "-r", "pi@camera-pi:" + REMOTE_DIRECTORY + "/.", LOCAL_DIRECTORY],
        ["scp", "pi@camera-pi:/home/pi/video/videolog.log", LOCAL_DIRECTORY],
    ]
    cleanup = [command for command in remote_commands(state) if command[0] == "rm"]
    assert cleanup == [
        ["rm", "-rf", "--", REMOTE_DIRECTORY],
        ["rm", "-f", "--", "/home/pi/video/videolog.log"],
    ]
    copy_indices = [index for index, (argv, _) in enumerate(state.calls) if argv[0] == "scp"]
    delete_indices = [
        index for index, (argv, _) in enumerate(state.calls)
        if argv[0] == "ssh" and len(argv) == 3 and shlex.split(argv[2])[0] == "rm"
    ]
    assert max(copy_indices) < min(delete_indices)
    assert all(options.get("check") is True for _, options in state.calls)


@pytest.mark.parametrize("failed_copy", [1, 2])
def test_windows_copy_failure_prevents_deletion(camera, camera_environment, failed_copy):
    """Accept fixtures/copy ordinal; assert any copy failure preserves all sources."""
    _, state = camera_environment
    copies = []

    def fail_copy(arguments):
        """Accept argv list; return bool failing the selected SCP invocation."""
        if arguments[0] == "scp":
            copies.append(arguments)
            return len(copies) == failed_copy
        return False

    state.fail = fail_copy
    with pytest.raises(subprocess.CalledProcessError):
        camera.video_stop_windows()
    assert not any(command[0] == "rm" for command in remote_commands(state))


@pytest.mark.parametrize("method", ["video_stop", "video_stop_windows"])
def test_stop_failure_prevents_transfer(camera, camera_environment, method):
    """Accept fixtures/method name; assert failed shutdown blocks copying and deletion."""
    _, state = camera_environment
    state.fail = lambda argv: is_process_operation(argv, "stop")
    with pytest.raises(subprocess.CalledProcessError):
        getattr(camera, method)()
    assert not any(argv[0] in ("scp", "rsync") for argv, _ in state.calls)
    assert not any(command[0] == "rm" for command in remote_commands(state))


def test_rsync_has_only_remote_sources(camera, camera_environment):
    """Accept fixtures; assert exactly two remote transfers with intact spaced paths."""
    _, state = camera_environment
    camera.video_stop()
    transfers = [argv for argv, _ in state.calls if argv[0] == "rsync"]
    assert len(transfers) == 2
    assert transfers[0][-2:] == ["pi@camera-pi:" + REMOTE_DIRECTORY + "/", LOCAL_DIRECTORY]
    assert transfers[1][-2:] == ["pi@camera-pi:/home/pi/video/*.log", LOCAL_DIRECTORY]
    assert all(options.get("check") is True for _, options in state.calls)


def test_rsync_failure_stops_remaining_transfers(camera, camera_environment, capsys):
    """Accept fixtures; assert first failure propagates without a success message."""
    _, state = camera_environment
    state.fail = lambda argv: argv[0] == "rsync"
    with pytest.raises(subprocess.CalledProcessError):
        camera.video_stop()
    assert sum(argv[0] == "rsync" for argv, _ in state.calls) == 1
    assert "rsync finished" not in capsys.readouterr().out


@pytest.mark.parametrize("failed_cleanup", ["directory", "log"])
def test_cleanup_failure_does_not_claim_sources_are_intact(
    camera, camera_environment, capsys, failed_cleanup,
):
    """Accept fixtures/stage; assert cleanup failure is propagated with accurate status."""
    _, state = camera_environment
    state.fail = lambda argv: (
        argv[0] == "ssh" and len(argv) == 3 and shlex.split(argv[2])[:2]
        == ["rm", "-rf" if failed_cleanup == "directory" else "-f"]
    )
    with pytest.raises(subprocess.CalledProcessError):
        camera.video_stop_windows()
    output = capsys.readouterr().out
    assert "NOT deleted" not in output
    assert "cleanup failed" in output.lower()
    if failed_cleanup == "log":
        assert "Recording directory removed" in output


@pytest.mark.parametrize("directory", ["", "/"])
def test_unsafe_recording_directory_cannot_be_deleted(camera, camera_environment, directory):
    """Accept fixtures/path string; assert empty/root paths cannot reach transfer or rm."""
    _, state = camera_environment
    camera.base_dir = directory
    state.resolved = directory
    with pytest.raises(ValueError):
        camera.video_stop_windows()
    assert not any(argv[0] == "scp" for argv, _ in state.calls)
    assert not any(command[0] == "rm" for command in remote_commands(state))


@pytest.mark.parametrize("operation, exits", [("stop", True), ("stop", False), ("check", True)])
def test_remote_process_control_targets_script_and_never_force_kills(
    camera_environment, monkeypatch, operation, exits,
):
    """Accept fixtures/mode/bool; simulate /proc and assert SIGINT, exit waiting and timeout."""
    module, _ = camera_environment
    signals = []
    ticks = iter(range(100))

    def read_process_file(path, mode):
        """Accept /proc path and binary mode; return fake NUL-separated command bytes."""
        if "/123/" in path:
            arguments = b"python3\0" + ACQUISITION_SCRIPT.encode() + b"\0session\0"
            if signals and exits:
                arguments = b""
        else:
            arguments = b"python3\0unrelated_experiment.py\0"
        return io.BytesIO(arguments)

    monkeypatch.setattr(builtins, "open", read_process_file)
    monkeypatch.setattr(os, "listdir", lambda path: ["123", "456", "self"])
    monkeypatch.setattr(os, "kill", lambda pid, number: signals.append((pid, number)))
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(sys, "argv", ["-c", ACQUISITION_SCRIPT, operation, "0.2"])
    if operation == "stop" and not exits:
        with pytest.raises(SystemExit, match="did not stop"):
            exec(module._CAMERA_PROCESS_CONTROL, {})
    else:
        exec(module._CAMERA_PROCESS_CONTROL, {})
    assert signals == ([(123, signal.SIGINT)] if operation == "stop" else [])


def test_legacy_windows_scp_quotes_remote_paths(camera, camera_environment):
    """Accept fixtures; assert legacy SCP copies all entries without the rejected '/.' source."""
    _, state = camera_environment
    state.ssh_version = "OpenSSH_for_Windows_8.1p1, LibreSSL 3.0.2"
    camera.video_stop_windows()
    transfers = [argv for argv, _ in state.calls if argv[:2] == ["scp", "-r"]]
    remote_paths = [shlex.split(argv[-2].split(":", 1)[1]) for argv in transfers]
    assert remote_paths == [[REMOTE_DIRECTORY + "/" + entry] for entry in state.entries]
    assert state.created_directories == [(LOCAL_DIRECTORY, True)]


def test_windows_destination_is_a_directory_before_any_copy(camera, camera_environment, monkeypatch):
    """Accept fixtures; assert directory-creation failure blocks copying and source deletion."""
    module, state = camera_environment

    def fail_directory_creation(path, exist_ok):
        """Accept destination str/bool; raise OSError to model an unavailable local drive."""
        raise OSError("Destination drive is unavailable")

    monkeypatch.setattr(module.os, "makedirs", fail_directory_creation)
    with pytest.raises(OSError, match="unavailable"):
        camera.video_stop_windows()
    assert not any(argv[0] == "scp" for argv, _ in state.calls)
    assert not any(command[0] == "rm" for command in remote_commands(state))


def test_unknown_scp_protocol_prevents_transfer(camera, camera_environment):
    """Accept fixtures; assert unknown SSH implementations cannot copy/delete by guessing."""
    _, state = camera_environment
    state.ssh_version = "Unknown SSH implementation"
    with pytest.raises(RuntimeError, match="OpenSSH"):
        camera.video_stop_windows()
    assert not any(argv[0] == "scp" for argv, _ in state.calls)
    assert not any(command[0] == "rm" for command in remote_commands(state))


def test_rsync_skips_logs_already_in_transferred_directory(camera, camera_environment):
    """Accept fixtures; assert removing a parent directory's files does not recopy removed logs."""
    _, state = camera_environment
    camera.base_dir = "/home/pi/video"
    state.resolved = camera.base_dir
    camera.video_stop()
    transfers = [argv for argv, _ in state.calls if argv[0] == "rsync"]
    assert len(transfers) == 1


@pytest.mark.parametrize("operation", ["stop", "check"])
def test_remote_process_control_handles_absent_camera(camera_environment, monkeypatch, operation):
    """Accept fixtures/mode; assert absent camera is stopped but cannot pass startup check."""
    module, _ = camera_environment
    monkeypatch.setattr(os, "listdir", lambda path: [])
    monkeypatch.setattr(sys, "argv", ["-c", ACQUISITION_SCRIPT, operation, "0.2"])
    if operation == "check":
        with pytest.raises(SystemExit, match="exited during startup"):
            exec(module._CAMERA_PROCESS_CONTROL, {})
    else:
        exec(module._CAMERA_PROCESS_CONTROL, {})
