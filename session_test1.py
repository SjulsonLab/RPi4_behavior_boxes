#!/usr/bin/env python3

from kelly_task import KellyTask

task = KellyTask("fentanyl")

task.start_session()

for i in range(3):
	print("starting trial")

	task.trial_start()

	while task.trial_running:
		task.run()

task.end

