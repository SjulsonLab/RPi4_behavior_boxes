"""Transfer recovery contracts, using fake processes and disposable real rsync data."""

import importlib
import os
import shlex
import shutil
import signal
import subprocess
from pathlib import Path

import pytest


class TransferProcess:
    """Fake child: accept return code/wait events; expose Popen's wait/poll API."""

    def __init__(self, returncode=0, events=()):
        """Accept int exit code and exception sequence; initialize a running child."""
        self.final_returncode = returncode
        self.events = list(events)
        self.returncode = None
        self.pid = 12345
        self.wait_timeouts = []

    def wait(self, timeout=None):
        """Accept timeout in seconds; raise the next event or return an int code."""
        self.wait_timeouts.append(timeout)
        if self.events:
            raise self.events.pop(0)
        self.returncode = self.final_returncode
        return self.returncode

    def poll(self):
        """Return int exit code when reaped, otherwise None."""
        return self.returncode


class TransferEnvironment:
    """Record child launches and sleeps; provide predetermined child results."""

    def __init__(self):
        """Initialize empty argv/options records and fake-process queue."""
        self.processes = []
        self.calls = []
        self.delays = []
        self.signals = []

    def popen(self, arguments, **options):
        """Accept argv/options; record them and return the next fake child."""
        self.calls.append((arguments, options))
        if self.processes:
            return self.processes.pop(0)
        return TransferProcess()

    def sleep(self, seconds):
        """Accept seconds; record the delay without waiting."""
        self.delays.append(seconds)

    def killpg(self, process_group, signal_number):
        """Accept integer process group/signal; record a cancellation request."""
        self.signals.append((process_group, signal_number))


@pytest.fixture
def transfer_module():
    """Return the production module; missing implementation is a RED failure."""
    return importlib.import_module("essential.file_transfer")


@pytest.fixture
def transfer_environment(monkeypatch, transfer_module):
    """Accept patch/module fixtures; return isolated subprocess/time doubles."""
    environment = TransferEnvironment()
    monkeypatch.setattr(transfer_module.subprocess, "Popen", environment.popen)
    monkeypatch.setattr(transfer_module.time, "sleep", environment.sleep)
    monkeypatch.setattr(transfer_module.os, "killpg", environment.killpg)
    return environment


@pytest.fixture
def transfer_arguments(tmp_path):
    """Return explicit paths/labels for one transfer; all paths are disposable."""
    return {
        "label": "Camera cam0",
        "source": "/home/pi/buffer/session",
        "destination": str(tmp_path / "external" / "session"),
        "log_path": str(tmp_path / "session_transfer.log"),
        "ssh_target": "pi@camera-pi",
    }


def test_success_shows_locations_and_uses_resumable_noninteractive_transfer(
    transfer_module, transfer_environment, transfer_arguments, capsys
):
    """Accept fixtures; assert success, visible output, and transport protections."""
    assert transfer_module.transfer_files(**transfer_arguments) is True
    command, options = transfer_environment.calls[0]
    assert "--partial-dir=.rsync-partial" in command
    assert "--timeout=120" in command
    ssh_command = shlex.split(command[command.index("-e") + 1])
    for setting in ("BatchMode=yes", "ConnectTimeout=10", "ServerAliveInterval=15", "ServerAliveCountMax=3"):
        assert setting in ssh_command
    assert options.get("stdout") is None
    assert options.get("stderr") != subprocess.PIPE
    assert options["start_new_session"] is True
    output = capsys.readouterr().out
    assert "pi@camera-pi:/home/pi/buffer/session/" in output
    assert transfer_arguments["destination"] in output
    assert transfer_arguments["log_path"] in output
    assert "succeeded" in output.lower()


def test_timeout_failure_retries_and_recovers(transfer_module, transfer_environment, transfer_arguments):
    """Accept fixtures; assert an rsync I/O timeout causes one delayed retry."""
    transfer_environment.processes = [TransferProcess(30), TransferProcess(0)]
    assert transfer_module.transfer_files(**transfer_arguments) is True
    assert len(transfer_environment.calls) == 2
    assert transfer_environment.delays == [5]
    report = Path(transfer_arguments["log_path"]).read_text()
    assert "30" in report
    assert "Retry" in report


def test_exhausted_retries_report_split_locations_and_copy_only_recovery(
    transfer_module, transfer_environment, transfer_arguments, capsys
):
    """Accept fixtures; assert bounded attempts and honest, nondeleting recovery."""
    transfer_environment.processes = [TransferProcess(12) for _ in range(5)]
    assert transfer_module.transfer_files(**transfer_arguments) is False
    assert len(transfer_environment.calls) == 5
    assert transfer_environment.delays == [5, 15, 30, 60]
    report = Path(transfer_arguments["log_path"]).read_text()
    assert "MANUAL RECOVERY REQUIRED" in report
    assert "already" in report.lower()
    assert "unverified" in report.lower()
    assert ".rsync-partial" in report
    recovery_line = next(line for line in report.splitlines() if line.startswith("rsync "))
    assert "--remove-source-files" not in shlex.split(recovery_line)
    assert "pi@camera-pi:/home/pi/buffer/session/" in recovery_line
    assert "succeeded" not in capsys.readouterr().out.lower()


def test_silent_healthy_process_keeps_running_and_repeats_locations(
    transfer_module, transfer_environment, transfer_arguments, capsys
):
    """Accept fixtures; wait timeouts emit reminders without killing a healthy child."""
    process = TransferProcess(events=[subprocess.TimeoutExpired("rsync", 30) for _ in range(3)])
    transfer_environment.processes = [process]
    assert transfer_module.transfer_files(**transfer_arguments) is True
    output = capsys.readouterr().out
    assert output.count("Still waiting") == 3
    assert output.count(transfer_arguments["destination"]) >= 4
    assert output.count("pi@camera-pi:/home/pi/buffer/session/") >= 4
    assert transfer_environment.signals == []
    assert process.wait_timeouts == [30, 30, 30, 30]


def test_cancellation_terminates_child_and_reports_locations(
    transfer_module, transfer_environment, transfer_arguments, capsys
):
    """Accept fixtures; Ctrl+C cleans up the process group then propagates cancellation."""
    process = TransferProcess(events=[KeyboardInterrupt(), subprocess.TimeoutExpired("rsync", 5)])
    transfer_environment.processes = [process]
    with pytest.raises(KeyboardInterrupt):
        transfer_module.transfer_files(**transfer_arguments)
    assert transfer_environment.signals == [(process.pid, signal.SIGTERM), (process.pid, signal.SIGKILL)]
    assert all(timeout is not None for timeout in process.wait_timeouts)
    output = capsys.readouterr().out
    assert "cancel" in output.lower()
    assert transfer_arguments["source"] in output
    assert transfer_arguments["destination"] in output


def test_launch_error_is_reported_with_recovery_locations(
    monkeypatch, transfer_module, transfer_environment, transfer_arguments, capsys
):
    """Accept fixtures; a missing rsync executable returns failure with usable paths."""
    def missing_executable(*args, **kwargs):
        """Accept subprocess arguments; raise the operating system's launch error."""
        raise FileNotFoundError("rsync is missing")

    monkeypatch.setattr(transfer_module.subprocess, "Popen", missing_executable)
    assert transfer_module.transfer_files(**transfer_arguments) is False
    output = capsys.readouterr().out
    assert "rsync is missing" in output
    assert transfer_arguments["source"] in output
    assert transfer_arguments["destination"] in output


def test_log_open_failure_does_not_prevent_transfer(
    transfer_module, transfer_environment, transfer_arguments, capsys, tmp_path
):
    """Accept fixtures; an unwritable log path falls back to visible terminal diagnostics."""
    transfer_arguments["log_path"] = str(tmp_path)  # Opening a directory must fail, even as root.
    assert transfer_module.transfer_files(**transfer_arguments) is True
    output = capsys.readouterr().out
    assert "log" in output.lower()
    assert "cannot" in output.lower() or "could not" in output.lower()
    assert transfer_arguments["source"] in output
    assert transfer_environment.calls[0][1].get("stderr") is None


@pytest.mark.parametrize("source", ["/home/pi/session 1", "/home/pi/mouse's session; $name"])
def test_remote_paths_and_printed_recovery_commands_preserve_literal_names(
    transfer_module, transfer_environment, transfer_arguments, source
):
    """Accept fixtures/path str; assert both local and remote shell quoting preserve paths."""
    transfer_arguments["source"] = source
    transfer_environment.processes = [TransferProcess(12) for _ in range(5)]
    transfer_module.transfer_files(**transfer_arguments)
    command = transfer_environment.calls[0][0]
    remote_path = command[-2].split(":", 1)[1]
    # -s passes filenames through the rsync protocol on both old and new rsync.
    assert "-s" in command
    assert remote_path == source + "/"
    report = Path(transfer_arguments["log_path"]).read_text()
    recovery_line = next(line for line in report.splitlines() if line.startswith("rsync "))
    assert shlex.split(recovery_line)[-2:] == command[-2:]


def test_report_is_appended_instead_of_replaced(transfer_module, transfer_environment, transfer_arguments):
    """Accept fixtures; preserve earlier session diagnostics on another transfer."""
    log_path = Path(transfer_arguments["log_path"])
    log_path.write_text("Earlier transfer diagnostics\n")
    assert transfer_module.transfer_files(**transfer_arguments) is True
    assert log_path.read_text().startswith("Earlier transfer diagnostics\n")


def popen_with_local_ssh(ssh_script, original_popen, arguments, **options):
    """Accept a fake SSH path/Popen/argv; execute real rsync without using a network."""
    command = list(arguments)
    ssh_index = command.index("-e") + 1
    command[ssh_index] = shlex.quote(str(ssh_script))
    return original_popen(command, **options)


def test_real_rsync_recovers_an_interrupted_video(transfer_module, tmp_path, monkeypatch, capfd):
    """Accept fixtures; interrupt a disposable remote-style copy, then verify recovery bytes."""
    if shutil.which("rsync") is None:
        pytest.skip("Real recovery integration requires the existing rsync executable")
    from functools import partial

    source_dir = tmp_path / "source"
    destination = tmp_path / "destination"
    source_dir.mkdir()
    destination.mkdir()
    video = source_dir / "video.h264"
    contents = bytes(range(256)) * 32768
    video.write_bytes(contents)
    ssh_script = tmp_path / "local_ssh.sh"
    ssh_script.write_text('#!/bin/sh\nshift\nexec /bin/sh -c "$*"\n')
    ssh_script.chmod(0o700)
    remote_source = "local:" + str(source_dir) + "/"
    command = ["rsync", "-av", "-s", "--partial-dir=.rsync-partial", "--bwlimit=1024", "-e", shlex.quote(str(ssh_script)), remote_source, str(destination)]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=0.5)
        process.send_signal(signal.SIGINT)
        process.communicate(timeout=10)
        assert process.returncode != 0
        assert video.exists()
        assert (destination / ".rsync-partial" / video.name).exists()
        original_popen = subprocess.Popen
        monkeypatch.setattr(transfer_module.subprocess, "Popen", partial(popen_with_local_ssh, ssh_script, original_popen))
        assert transfer_module.transfer_files(
            label="Camera cam0", source=str(source_dir), destination=str(destination),
            log_path=str(tmp_path / "transfer.log"), ssh_target="local",
        ) is True
        assert (destination / video.name).read_bytes() == contents
        assert not video.exists()
        assert not (destination / ".rsync-partial" / video.name).exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
