#!/usr/bin/env python3

from kelly_task import KellyTask

# put all session-specific parameters here, e.g. mouse name, name of protocol, etc.













# initiate task object
task = KellyTask("fentanyl")


# start session
task.start_session()


# loop over trials
for i in range(3):



	print("starting trial")

	task.trial_start()

	while task.trial_running:
		task.run()

task.end_session()



