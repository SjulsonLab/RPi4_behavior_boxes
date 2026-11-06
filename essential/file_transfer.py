"""Retry session-file moves and keep their recovery locations visible.

This module uses Python 3.7's standard library and the installed rsync/SSH tools.
Rsync handles transfer integrity, partial downloads, and per-file source removal.
Network inactivity is bounded; kernel-level disk waits may still need intervention.
"""

import os
import shlex
import signal
import subprocess
import time
from datetime import datetime
from typing import List, Optional, Tuple


def transfer_files(
        label: str, source: str, destination: str, log_path: str,
        ssh_target: Optional[str] = None, max_attempts: int = 5,
        retry_delays: Tuple[int, ...] = (5, 15, 30, 60),
        heartbeat_seconds: float = 30.0, inactivity_seconds: int = 120,
) -> bool:
    """Move one directory's contents, retrying ordinary rsync/OS failures.

    Inputs are scalar path/label strings; ``ssh_target`` is ``user@host`` or None
    for a local source. ``log_path`` names an append-only file outside the source
    directory. Attempt counts are positive integers; delays and heartbeat are in
    seconds. ``inactivity_seconds`` limits rsync I/O inactivity, not total runtime.
    Returns bool success after a zero rsync exit code. Failed/untransferred files
    may remain at source while completed files have already moved to destination.
    Ctrl+C terminates the local process group and raises KeyboardInterrupt so the
    caller can stop subsequent transfers. Requires an already validated mount.
    """
    command = _rsync_command(source, destination, ssh_target, inactivity_seconds)
    details = transfer_locations(label, source, destination, log_path, ssh_target)
    try:
        for attempt in range(1, max_attempts + 1):
            report_transfer("{} — attempt {}/{}\n{}".format(label, attempt, max_attempts, details), log_path)
            try:
                returncode = _run_attempt(command, label, details, log_path, heartbeat_seconds)
                if returncode == 0:
                    report_transfer("{}: transfer succeeded.".format(label), log_path)
                    return True
                report_transfer("{}: rsync failed with exit code {}.".format(label, returncode), log_path)
            except OSError as error:
                report_transfer("{}: transfer could not run: {}".format(label, error), log_path)

            if attempt < max_attempts:
                delay = retry_delays[min(attempt - 1, len(retry_delays) - 1)]
                report_transfer("Retry {} in {} seconds.\n{}".format(label, delay, details), log_path)
                time.sleep(delay)
    except KeyboardInterrupt:
        report_transfer("{}: transfer cancelled.\n{}".format(label, details), log_path)
        raise

    report_transfer("{}: TRANSFER INCOMPLETE — MANUAL RECOVERY REQUIRED\n{}".format(label, details), log_path)
    return False


def transfer_locations(
        label: str, source: str, destination: str, log_path: str,
        ssh_target: Optional[str] = None,
) -> str:
    """Return human-readable locations and a copy-only recovery command.

    Inputs are scalar label/path strings and optional ``user@host``. Source and
    destination directory contents are not inventoried. Returns str describing
    where to check, including incomplete downloads; remote contents are unverified.
    The recovery command retains originals for inspection after a manual copy.
    """
    source_directory = source.rstrip("/") + "/"
    source_location = "{}:{}".format(ssh_target, source_directory) if ssh_target else source_directory
    recovery = _rsync_command(source, destination, ssh_target, 120)
    recovery.remove("--remove-source-files")
    return (
        "{label}\nSource to check: {source}\nDestination to check: {destination}\n"
        "Completed files may already be at the destination; remaining files may be at the source.\n"
        "Source contents are unverified until checked, especially if a camera is unreachable.\n"
        "Partial downloads are incomplete: .rsync-partial directories under the destination.\n"
        "Transfer log: {log}\nCopy-only recovery command (check the external mount first):\n{command}"
    ).format(label=label, source=source_location, destination=destination,
             log=log_path, command=" ".join(shlex.quote(argument) for argument in recovery))


def report_transfer(message: str, log_path: Optional[str]) -> None:
    """Print str status immediately and append it to optional scalar log-file path.

    Returns None. Log errors are shown on the terminal without preventing copying.
    This deliberately does not depend on the session logger, which is closed before
    transfers start. Existing log contents are preserved.
    """
    print(message, flush=True)
    if log_path is not None:
        try:
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write("[{}] {}\n".format(datetime.now().isoformat(), message))
        except OSError as error:
            print("Cannot write transfer log {}: {}. Use the terminal recovery information.".format(log_path, error), flush=True)


# Helpers: command construction and supervision of one local rsync process group.
def _rsync_command(source: str, destination: str, ssh_target: Optional[str], inactivity_seconds: int) -> List[str]:
    """Accept scalar paths/optional user@host and seconds; return literal rsync argv.

    The source's contents are moved into destination. Remote filenames travel via
    rsync's protocol (-s, supported since rsync 3.0), avoiding remote-shell quoting
    differences between the old Pi tools and newer rsync releases.
    """
    command = ["rsync", "-av" if ssh_target else "-arvz", "--progress", "--remove-source-files",
               "--timeout={}".format(inactivity_seconds)]
    source_directory = source.rstrip("/") + "/"
    if ssh_target:
        command.extend([
            "-s", "--partial-dir=.rsync-partial", "-e",
            "ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3",
        ])
        source_directory = "{}:{}".format(ssh_target, source_directory)
    command.extend([source_directory, destination])
    return command


def _run_attempt(command: List[str], label: str, details: str, log_path: str, heartbeat_seconds: float) -> int:
    """Accept argv/status strings/log path and seconds; return one child exit code.

    Stdout goes directly to the terminal; stderr appends to the log, or inherits
    the terminal if the log cannot open. Timed waits emit reminders without imposing
    a total transfer deadline. KeyboardInterrupt cleans up children, then propagates.
    """
    error_log = None
    error_offset = 0
    try:
        try:
            error_log = open(log_path, "ab", buffering=0)
            error_offset = error_log.tell()
        except OSError as error:
            report_transfer("Cannot open transfer log {}: {}. Errors will appear on the terminal.".format(log_path, error), None)

        started = time.monotonic()
        process = subprocess.Popen(command, stdout=None, stderr=error_log,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            while True:
                try:
                    returncode = process.wait(timeout=heartbeat_seconds)
                    break
                except subprocess.TimeoutExpired:
                    elapsed = int(time.monotonic() - started)
                    report_transfer("Still waiting for {} ({} seconds elapsed).\n{}".format(label, elapsed, details), log_path)
        except KeyboardInterrupt:
            _terminate_transfer(process)
            raise

        if returncode != 0 and error_log is not None:
            _show_error_excerpt(log_path, error_offset)
        return returncode
    finally:
        if error_log is not None:
            error_log.close()


def _show_error_excerpt(log_path: str, start_offset: int) -> None:
    """Accept a log path and attempt's byte offset; print up to its last 4096 bytes.

    Returns None. Full stderr remains in the append-only report. Read failures only
    warn; they must not prevent another transfer attempt.
    """
    try:
        with open(log_path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(start_offset, handle.tell() - 4096))
            excerpt = handle.read().decode("utf-8", errors="replace").strip()
        if excerpt:
            print("Transfer diagnostics:\n{}".format(excerpt), flush=True)
    except OSError as error:
        print("Could not read transfer diagnostics {}: {}".format(log_path, error), flush=True)


def _terminate_transfer(process: subprocess.Popen) -> None:
    """Accept our session-isolated child; signal its group and wait at most 5 s twice.

    Returns None. SIGTERM permits rsync's normal partial-file cleanup; SIGKILL is a
    fallback. An unreaped child (e.g. kernel disk wait) is explicitly reported.
    """
    for signal_number in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, signal_number)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            pass
    print("Transfer process group {} did not exit; check it before manual recovery.".format(process.pid), flush=True)
