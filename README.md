# RPi4_behavior_boxes
BehavBox is a system with Raspberry Pi computers that is sufficient to provide a foundation of constructing animal behavior training and experiment.

# Quick Start
in task_protocol, you could find all the task examples. Each task has its run file, task file, task information file and an example of session_information file.

To start running a task file, you need to first create a session_information pathway and session_information file in a path (suggested) in the home directory and outside of the git repo since you would have to configure and changes the file everyday for training purposes.

After configure the session_information path and input the appropriate path leading to the exact session_information of the date, you could do python3 run_x_task.py to start running the task.
