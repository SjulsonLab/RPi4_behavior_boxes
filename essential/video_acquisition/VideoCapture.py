#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Control standalone PiCamera recording and transfer recordings from a Pi.

Created on Fri Oct 28 12:30:51 2022 by eliezyer, based on the BehavBox class.

The Pi acquisition script records at a fixed 30 frames/second. Commands run on
the local computer through OpenSSH; only explicitly quoted commands run on the Pi.
"""

import json
import os
import posixpath
import re
import shlex
import socket
import subprocess
import time

from colorama import Fore, Style


_PREVIEW_SCRIPT = "/home/pi/RPi4_behavior_boxes/video_acquisition/start_preview.py"
_ACQUISITION_SCRIPT = "/home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.py"
_VIDEO_LOG = "/home/pi/video/videolog.log"

# This code runs on the Linux Pi, not the Windows controller. Match an actual
# script argument rather than a substring of another process's command line.
_CAMERA_PROCESS_CONTROL = r'''
import os
import signal
import sys
import time

script, operation, timeout = sys.argv[1:]

def matches_process(pid):
    """Accept a PID string; return bool for a live invocation of the target script."""
    try:
        with open("/proc/" + pid + "/cmdline", "rb") as command_file:
            arguments = command_file.read().split(b"\0")
        return os.fsencode(script) in arguments[:2]
    except (FileNotFoundError, ProcessLookupError):
        return False

process_ids = [
    pid for pid in os.listdir("/proc")
    if pid.isdigit() and matches_process(pid)
]
if operation == "check":
    if not process_ids:
        raise SystemExit("Acquisition exited during startup; check ~/video/videolog.log")
else:
    for pid in process_ids:
        try:
            os.kill(int(pid), signal.SIGINT)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + float(timeout)
    while process_ids:
        process_ids = [pid for pid in process_ids if matches_process(pid)]
        if not process_ids:
            break
        if time.monotonic() >= deadline:
            raise SystemExit("Camera process did not stop; no transfer or forced kill performed")
        time.sleep(0.1)
'''


class VideoCapture:
    """Record video on a Pi and move a whole recording directory to local storage.

    Inputs to construction are strings: `IP_address_video` is a hostname/IP,
    `video_name` is a filename prefix, `base_pi_dir` is the Pi recording directory,
    and `local_storage_dir` is the destination on the controller. Pi paths use
    POSIX conventions; local paths use the controller's conventions. `frame_rate`
    is a numeric scalar in frames/second and must equal 30. Construction returns
    a VideoCapture instance; operations return None and propagate failures.

    Transfers include the entire Pi directory, not just this filename prefix.
    Windows transfers use the paired OpenSSH ssh/scp tools from one installation.
    """

    # Public camera-control and transfer methods.
    def __init__(self, IP_address_video, video_name, base_pi_dir,
                 local_storage_dir, frame_rate=30):
        """Accept the class's documented scalar inputs; initialize an instance, no I/O."""
        if frame_rate != 30:
            raise ValueError("The acquisition script records at a fixed 30 frames/second.")
        self.IP_address_video = IP_address_video
        self.basename = video_name
        self.base_dir = base_pi_dir
        self.local_storage_dir = local_storage_dir
        self.frame_rate = frame_rate

    def video_preview_only(self):
        """Accept no arguments; preview until Ctrl-C, return None, propagate SSH failures."""
        self._stop_camera_process(_ACQUISITION_SCRIPT)
        self._stop_camera_process(_PREVIEW_SCRIPT)
        self._show_preview("CTRL + C to quit previewing")

    def video_start(self):
        """Accept no arguments; start fixed-30-fps acquisition, return None or raise.

        Uses the configured Pi directory and filename prefix. The startup check
        establishes process survival, not proof of recorded frames.
        """
        if self.frame_rate != 30:
            raise ValueError("The acquisition script records at a fixed 30 frames/second.")
        directory = self._resolve_remote_directory()
        self._stop_camera_process(_ACQUISITION_SCRIPT)
        self._stop_camera_process(_PREVIEW_SCRIPT)
        self._show_preview("CTRL + C to quit previewing and start recording")

        self._run_remote(
            "mkdir -p -- " + shlex.quote(directory) + " "
            + shlex.quote(posixpath.dirname(_VIDEO_LOG))
        )
        self._run_remote("date >> " + shlex.quote(_VIDEO_LOG))
        filename = directory + "/" + self.basename
        # The acquisition script's optional second argument is a camera ID,
        # not a frame rate. Omit it to use that script's default camera ID.
        self._run_remote(
            "nohup " + shlex.quote(_ACQUISITION_SCRIPT) + " "
            + shlex.quote(filename) + " </dev/null >> "
            + shlex.quote(_VIDEO_LOG) + " 2>&1 &"
        )
        # Acquisition currently includes five seconds of camera warm-up sleeps.
        time.sleep(7)
        self._camera_process_operation(_ACQUISITION_SCRIPT, "check")
        print(Fore.GREEN + "\nRecording process is running at 30 fps." + Style.RESET_ALL)
        print(
            Fore.RED + Style.BRIGHT
            + "Please check that the recording preview is on."
            + Style.RESET_ALL
        )

    def video_stop(self):
        """Accept no arguments; stop, then move all recording files/logs using rsync.

        Returns None on success. Raises on shutdown/transfer failure. Rsync removes
        successfully transferred source files; partial failure can leave some
        files at the destination and others on the Pi.
        """
        directory = self._prepare_transfer()
        remote_sources = [directory + "/"]
        # A parent-directory transfer already moves its log files. Trying the
        # wildcard afterwards would fail because rsync removed those sources.
        if posixpath.commonpath((directory, _VIDEO_LOG)) != directory:
            remote_sources.append("/home/pi/video/*.log")
        for remote_source in remote_sources:
            subprocess.run([
                "rsync", "-av", "--protect-args", "--progress", "--remove-source-files",
                "pi@" + self.IP_address_video + ":" + remote_source,
                os.fspath(self.local_storage_dir),
            ], check=True)
        print("rsync finished!")

    def video_stop_windows(self):
        """Accept no arguments; stop, copy the whole directory/log, then delete sources.

        Returns None on success; raises on failure. Requires paired OpenSSH ssh/scp.
        Both copies must succeed before deletion. Cleanup errors can leave partial
        source deletion and are reported separately from copy errors.
        """
        directory = self._prepare_transfer()
        destination = os.fspath(self.local_storage_dir)
        uses_sftp = self._scp_uses_sftp()
        print("Copying video files to local storage...")
        try:
            # A missing destination must become a directory, not the filename
            # of the first copied entry when legacy SCP copies files individually.
            os.makedirs(destination, exist_ok=True)
            for source in self._scp_recording_sources(directory, uses_sftp):
                subprocess.run([
                    "scp", "-r", "pi@" + self.IP_address_video + ":" + source,
                    destination,
                ], check=True)
            subprocess.run([
                "scp", "pi@" + self.IP_address_video + ":" + _VIDEO_LOG, destination,
            ], check=True)
        except (subprocess.CalledProcessError, OSError):
            print("Copy failed. No source deletion was attempted.")
            raise

        print("Copy finished successfully.")
        try:
            self._run_remote("rm -rf -- " + shlex.quote(directory))
            print("Recording directory removed from Raspberry Pi.")
            self._run_remote("rm -f -- " + shlex.quote(_VIDEO_LOG))
        except (subprocess.CalledProcessError, OSError):
            print("Source cleanup failed; some source files may already have been removed.")
            raise
        print("Video transfer finished!")

    # Private helpers: commands are kept here to apply the same checks everywhere.
    def _scp_recording_sources(self, directory, uses_sftp):
        """Accept absolute Pi directory str/protocol bool; return list[str] SCP paths.

        SFTP accepts directory/. to copy all contents. Legacy SCP rejects that
        basename, so list every entry (including hidden files) on the Pi and
        shell-quote each path. SCP's recursive flag also copies subdirectories.
        """
        if uses_sftp:
            return [directory + "/."]
        code = "import json, os, sys; print(json.dumps(os.listdir(sys.argv[1])))"
        result = self._run_remote(
            "python3 -c " + shlex.quote(code) + " " + shlex.quote(directory),
            capture_output=True,
        )
        return [shlex.quote(directory + "/" + entry) for entry in json.loads(result.stdout)]

    def _scp_uses_sftp(self):
        """Accept no arguments; return bool for paired OpenSSH scp's default protocol.

        OpenSSH 9+ uses SFTP; older releases use a remote shell. Version output
        comes from the matching local ssh tool. Unknown implementations raise
        RuntimeError rather than guessing which remote-path quoting is safe.
        """
        result = subprocess.run(
            ["ssh", "-V"], check=True, capture_output=True, text=True,
        )
        version_text = (result.stdout or "") + (result.stderr or "")
        version = re.search(r"OpenSSH(?:_for_Windows)?_(\d+)\.", version_text)
        if version is None:
            raise RuntimeError("Cannot determine the paired OpenSSH ssh/scp version.")
        return int(version.group(1)) >= 9

    def _run_remote(self, command, capture_output=False):
        """Run a quoted POSIX command string on the Pi using checked SSH.

        Inputs: command str, capture_output bool (default False). Returns a
        subprocess.CompletedProcess; captured stdout/stderr are strings with no
        physical units. Raises CalledProcessError/OSError on failure.
        """
        return subprocess.run([
            "ssh", "pi@" + self.IP_address_video, command,
        ], check=True, text=True, capture_output=capture_output)

    def _resolve_remote_directory(self):
        """Accept no arguments; return an absolute POSIX directory string from the Pi.

        Expands Pi-side ~ and symlinks. Rejects empty paths, the filesystem root,
        and the SSH user's home directory before any destructive operation.
        """
        directory = os.fspath(self.base_dir)
        if not directory.strip():
            raise ValueError("The Pi recording directory must not be empty.")
        code = (
            "import os, sys\n"
            "directory = os.path.realpath(os.path.expanduser(sys.argv[1]))\n"
            "home = os.path.realpath(os.path.expanduser('~'))\n"
            "if directory in ('/', home):\n"
            "    raise SystemExit('Unsafe Pi recording directory')\n"
            "print(directory)\n"
        )
        result = self._run_remote(
            "python3 -c " + shlex.quote(code) + " " + shlex.quote(directory),
            capture_output=True,
        )
        resolved = result.stdout.rstrip("\n")
        if not resolved.startswith("/") or resolved == "/":
            raise ValueError("Unsafe Pi recording directory: " + repr(resolved))
        return resolved

    def _camera_process_operation(self, script, operation):
        """Accept absolute script path and 'stop'/'check' strings; return None or raise.

        Stop sends SIGINT only to matching scripts and waits up to 30 seconds.
        Check requires a matching live process. Linux /proc is read on the Pi.
        """
        self._run_remote(" ".join(shlex.quote(argument) for argument in (
            "python3", "-c", _CAMERA_PROCESS_CONTROL, script, operation, "30",
        )))

    def _stop_camera_process(self, script):
        """Accept an absolute Pi script path string; return None after graceful exit.

        An absent process counts as stopped. Shutdown timeout raises through SSH
        without force-killing the process or proceeding to transfer.
        """
        self._camera_process_operation(script, "stop")

    def _show_preview(self, instructions):
        """Accept a display instruction string; preview and clean up, returning None.

        Ctrl-C ends preview normally; other command failures propagate. Cleanup
        waits for the remote camera process even if the local SSH client exited.
        """
        print(Fore.CYAN + "\nStart Previewing ..." + Style.RESET_ALL)
        print(Fore.RED + "\n" + instructions + Style.RESET_ALL)
        try:
            self._run_remote(shlex.quote(_PREVIEW_SCRIPT))
        except KeyboardInterrupt:
            print(Fore.GREEN + "\nPreview interrupted." + Style.RESET_ALL)
        finally:
            self._stop_camera_process(_PREVIEW_SCRIPT)

    def _prepare_transfer(self):
        """Accept no arguments; validate, stop acquisition, prompt, return Pi directory str.

        No transfer occurs if validation or graceful shutdown fails. The returned
        path is absolute and uses POSIX conventions, with no physical units.
        """
        directory = self._resolve_remote_directory()
        self._stop_camera_process(_ACQUISITION_SCRIPT)
        print("Moving video files from " + self.IP_address_video + " to " + socket.gethostname() + ":")
        input("Press Enter to continue with copying the videos to the local storage...")
        return directory
