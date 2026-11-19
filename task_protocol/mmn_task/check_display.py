"""Print Raspberry Pi boot, desktop, and display diagnostics."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def _run(label: str, command: List[str]) -> None:
    print("\n{}:".format(label))
    if shutil.which(command[0]) is None:
        print("  command not found: {}".format(command[0]))
        return

    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
    )
    output = result.stdout.strip()
    print(output if output else "  (no output)")
    if result.returncode:
        print("  exit status: {}".format(result.returncode))


def _read_file(path: Path) -> Optional[str]:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def main() -> int:
    print("Raspberry Pi display diagnostics")
    print("DISPLAY={!r}".format(os.environ.get("DISPLAY", "")))
    print("WAYLAND_DISPLAY={!r}".format(os.environ.get("WAYLAND_DISPLAY", "")))

    _run("Default boot target", ["systemctl", "get-default"])
    _run(
        "Display manager status",
        ["systemctl", "status", "display-manager", "--no-pager"],
    )
    _run(
        "Desktop package status",
        [
            "dpkg-query",
            "-W",
            "-f=${binary:Package}: ${db:Status-Status}\n",
            "lightdm",
            "raspberrypi-ui-mods",
            "lxsession",
            "xserver-xorg",
        ],
    )

    drm_dir = Path("/sys/class/drm")
    print("\nDRM connectors:")
    connectors = sorted(drm_dir.glob("card*-*"))
    found_connector = False
    for connector in connectors:
        status = _read_file(connector / "status")
        if status is not None:
            found_connector = True
            print("  {}: {}".format(connector.name, status))
    if not found_connector:
        print("  no connector status files found")

    if os.environ.get("DISPLAY"):
        _run("X display layout", ["xrandr", "--query"])
    else:
        print("\nX display layout:")
        print("  DISPLAY is unset; xrandr cannot query a desktop from this shell")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
