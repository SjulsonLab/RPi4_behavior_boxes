# RPi4_behavior_boxes
BehavBox is a system with Raspberry Pi computers that is sufficient to provide a foundation of constructing animal 
behavior training and experiment.

# Quick Start
All task parameters are set through the session_info.py file. After configuring the session info, 
run python3 main.py to start running the task.

# Multi-camera setup
To enable multiple remote camera Raspberry Pis, set the following in `session_info.py`:
- `use_multiple_cameras = True`
- configure `camera_nodes` with one entry per camera node:
  - `camera_id` unique ID (for file naming/output folders)
  - `host` camera Raspberry Pi IP/hostname
  - `ssh_user` usually `pi`
  - `backend` one of `picamera` or `picamera2`
  - `required` set `True` for nodes that must be present

In multi-camera mode, startup now verifies all required camera nodes before the task begins.

# Camera dry-run
Run camera/network verification without starting the behavior task:

`python3 main.py --camera-dry-run`

This checks SSH reachability, required remote acquisition scripts, and camera backend initialization on each configured camera node.
