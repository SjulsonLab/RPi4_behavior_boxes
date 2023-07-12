# RPi4_behavior_boxes
BehavBox is a system with Raspberry Pi computers that is sufficient to provide a foundation of constructing animal behavior training and experiment.

# Quick Start
in task_protocol, you could find all the task examples. Each task has its run file, task file, task information file and an example of session_information file.

To start running a task file, you need to first create a session_information pathway and session_information file in a path (suggested) in the home directory and outside of the git repo since you would have to configure and changes the file everyday for training purposes.

After configure the session_information path and input the appropriate path leading to the exact session_information of the date, you could do python3 run_x_task.py to start running the task.

# Example
To start running the task `headfixed_task.py`
1. Setup and configure the 'session_information_year-month-date.py' file:
first, create the experimental_data directory in the home directory path: 
`$ mkdir ~/experimental_data`\
second, create all the necessary subdirectories for the specific task: 
`$ mkdir ~/experimental_data/headfixed_task`\
`$ mkdir ~/experimental_data/headfixed_task/session_info`\
then, copy the session_information example file corresponding to the specific task:
`$ cp ~/RPi4_behavbior_boxes/task_protocol/headfixed_task/session_info_headfixed_independent_reward.py ~/experimental_data/headfixed_task/session_info`\
2. Modify the newly created session_info file:
`$ sudo nano ~/experimental_data/headfixed_task/session_info_headfixed_independent_reward.py`
**KEEP IN MIND** after configuring the session_information to manually change the field manual date to the day of the experiment session (the day of the experiment), and the name of the session_info file from `session_info_headfixed_independent_reward.py` to `session_info_year-month-date.py`. Otherwise, an error would occur when running the task file.
3. After setting up the session_info file, run the task:
`$ python3 ~/RPi4_behavior_boxes/task_protocol/headfixed_task/run_headfixed_task.py`