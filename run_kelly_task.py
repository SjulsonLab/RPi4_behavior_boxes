#!/usr/bin/env python3

from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
from icecream import ic
import logging
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
import logging.config
import pysistence, collections
import socket

# all modules above this line will have logging disabled
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

# import your task class here
from kelly_task import KellyTask

# import session and mouse info
from session_info import session_info
from session_info import mouse_info


# make data directory and initialize logfile
os.makedirs( session_info['dirname'] )
os.chdir( session_info['dirname'] )
filename = session_info['mouse_name'] + "_" + session_info['datetime'] + ".log" 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
    datefmt=('%Y-%m-%d,%H:%M:%S'),
    handlers=[
        logging.FileHandler(filename),
        logging.StreamHandler()
    ]
)

# initiate task object
task = KellyTask("fentanyl")


# start session
task.start_session()


# loop over trials
for i in range(3):


	logging.info("starting trial")
	print("starting trial")

	task.trial_start()

	while task.trial_running:
		task.run()

task.end_session()



