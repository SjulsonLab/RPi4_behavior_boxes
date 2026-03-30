#!/usr/bin/env python3

import argparse
import shlex
import subprocess
import sys
from typing import Dict, List, Optional


DEFAULT_SEARCH_ROOTS = [
    "/home/pi/RPi4_behavior_boxes",
    "/home/pi/RPi4_behavior_boxes/video_acquisition",
]


def expected_camera_files(backend: str) -> Dict[str, str]:
    if backend == "picamera2":
        return {
            "preview": "/home/pi/RPi4_behavior_boxes/video_acquisition/preview_v3_camera.py",
            "recording": "/home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_picamera2.sh",
            "stop": "/home/pi/RPi4_behavior_boxes/video_acquisition/stop_acquisition_picamera2.sh",
        }
    return {
        "preview": "/home/pi/RPi4_behavior_boxes/video_acquisition/start_preview.py",
        "recording": "/home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.sh",
        "stop": "/home/pi/RPi4_behavior_boxes/video_acquisition/stop_acquisition.sh",
    }


def alternate_names_by_role(backend: str) -> Dict[str, List[str]]:
    preview_names = [
        "start_preview.py",
        "start_preview_picamera2.py",
        "preview_v3_camera.py",
    ]
    recording_names = [
        "start_acquisition.sh",
        "start_acquisition_picamera2.sh",
        "start_acquisition.py",
        "start_acquisition_picamera2.py",
        "start_acquisition_v3_camera.py",
    ]
    stop_names = [
        "stop_acquisition.sh",
        "stop_acquisition_picamera2.sh",
    ]

    if backend == "picamera2":
        preview_names = [
            "preview_v3_camera.py",
            "start_preview_picamera2.py",
            "start_preview.py",
        ]
        recording_names = [
            "start_acquisition_picamera2.sh",
            "start_acquisition_v3_camera.py",
            "start_acquisition_picamera2.py",
            "start_acquisition.sh",
            "start_acquisition.py",
        ]
        stop_names = [
            "stop_acquisition_picamera2.sh",
            "stop_acquisition.sh",
        ]

    return {
        "preview": preview_names,
        "recording": recording_names,
        "stop": stop_names,
    }


def ssh_run(
    target: str,
    command: str,
    *,
    timeout: int = 10,
) -> subprocess.CompletedProcess:
    remote_command = f"bash -lc {shlex.quote(command)}"
    return subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={timeout}",
            target,
            remote_command,
        ],
        capture_output=True,
        text=True,
    )


def check_exact_path(target: str, path: str) -> bool:
    result = ssh_run(target, f"test -f {shlex.quote(path)}", timeout=5)
    return result.returncode == 0


def search_remote_paths(target: str, roots: List[str], names: List[str]) -> List[str]:
    root_clause = " ".join(shlex.quote(root) for root in roots)
    name_clause = " -o ".join(f"-name {shlex.quote(name)}" for name in names)
    command = (
        f"find {root_clause} -maxdepth 2 -type f \\( {name_clause} \\) "
        "2>/dev/null | sort -u"
    )
    result = ssh_run(target, command, timeout=20)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def load_camera_node_from_session(camera_id: Optional[str]) -> Dict[str, str]:
    from session_info import make_session_info

    session_info = make_session_info()
    camera_nodes = session_info.get("camera_nodes", [])
    if not camera_nodes:
        raise RuntimeError("session_info did not provide any camera_nodes")

    if camera_id is not None:
        for node in camera_nodes:
            if node.get("camera_id") == camera_id:
                return {
                    "camera_id": str(node.get("camera_id", "cam0")),
                    "host": str(node.get("host", "")),
                    "ssh_user": str(node.get("ssh_user", "pi")),
                    "backend": str(node.get("backend", "picamera2")),
                }
        raise RuntimeError(f"Could not find camera_id={camera_id!r} in session_info")

    node = camera_nodes[0]
    return {
        "camera_id": str(node.get("camera_id", "cam0")),
        "host": str(node.get("host", "")),
        "ssh_user": str(node.get("ssh_user", "pi")),
        "backend": str(node.get("backend", "picamera2")),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Debug SSH camera path checks on the remote camera Pi."
    )
    parser.add_argument("--host", help="Camera Pi host or IP address.")
    parser.add_argument(
        "--ssh-user",
        default="pi",
        help="SSH user for the camera Pi. Default: pi",
    )
    parser.add_argument(
        "--backend",
        choices=["picamera", "picamera2"],
        help="Camera backend to inspect.",
    )
    parser.add_argument(
        "--camera-id",
        default="cam0",
        help="Camera node ID to report. Default: cam0",
    )
    parser.add_argument(
        "--from-session",
        action="store_true",
        help="Load host/user/backend from session_info.make_session_info().",
    )
    return parser.parse_args()


def resolve_camera_node(args: argparse.Namespace) -> Dict[str, str]:
    if args.from_session:
        return load_camera_node_from_session(args.camera_id)

    if not args.host or not args.backend:
        raise RuntimeError(
            "Provide --host and --backend, or use --from-session."
        )

    return {
        "camera_id": args.camera_id,
        "host": args.host,
        "ssh_user": args.ssh_user,
        "backend": args.backend,
    }


def print_role_report(
    role: str,
    expected_path: str,
    exact_exists: bool,
    matches: List[str],
) -> None:
    status = "FOUND" if exact_exists else "MISSING"
    print(f"\n{role}: {status}")
    print(f"  expected path: {expected_path}")
    print(f"  exact path exists: {'yes' if exact_exists else 'no'}")

    alternate_matches = [match for match in matches if match != expected_path]
    if alternate_matches:
        print("  alternate matches:")
        for match in alternate_matches:
            print(f"    {match}")
    else:
        print("  alternate matches: none")


def main() -> int:
    try:
        args = parse_args()
        camera_node = resolve_camera_node(args)
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    target = f"{camera_node['ssh_user']}@{camera_node['host']}"
    backend = camera_node["backend"]
    expected_files = expected_camera_files(backend)
    alternate_names = alternate_names_by_role(backend)

    print(f"camera_id: {camera_node['camera_id']}")
    print(f"ssh target: {target}")
    print(f"backend: {backend}")

    sanity_result = ssh_run(target, "echo camera_ping && whoami && hostname && pwd", timeout=5)
    if sanity_result.returncode != 0:
        print("\nSSH sanity check failed.")
        stderr = sanity_result.stderr.strip()
        if stderr:
            print(stderr)
        return 1

    sanity_lines = [line.strip() for line in sanity_result.stdout.splitlines() if line.strip()]
    remote_user = sanity_lines[1] if len(sanity_lines) > 1 else "<unknown>"
    remote_hostname = sanity_lines[2] if len(sanity_lines) > 2 else "<unknown>"
    remote_pwd = sanity_lines[3] if len(sanity_lines) > 3 else "<unknown>"

    print("\nSSH sanity check:")
    for line in sanity_lines:
        print(f"  {line}")

    exact_found = 0
    for role, expected_path in expected_files.items():
        matches = search_remote_paths(
            target,
            DEFAULT_SEARCH_ROOTS,
            alternate_names[role],
        )
        exact_exists = check_exact_path(target, expected_path)
        if exact_exists:
            exact_found += 1
        print_role_report(role, expected_path, exact_exists, matches)

    print("\nSummary:")
    print(f"  remote user: {remote_user}")
    print(f"  remote hostname: {remote_hostname}")
    print(f"  remote pwd: {remote_pwd}")
    print(f"  exact expected files found: {exact_found}/3")
    if exact_found == 3:
        print("  all expected camera files are present at the exact paths")
        return 0

    print("  one or more expected paths are missing")
    return 1


if __name__ == "__main__":
    sys.exit(main())
