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

# defining immutable mouse dict (once defined for a mouse, this should never change)
mouse_info = pysistence.make_dict({'mouse_name': 'mouse01',
                 'fake_field': 'fake_info',
                 })

# Information for this session (the user should edit this each session)
session_info                              	= collections.OrderedDict()
session_info['mouse_name']                 	= mouse_info['mouse_name']
#session_info['trainingPhase']             	= 4
session_info['basedir']					  	= '/home/pi/fakedata'
session_info['weight']                	    = 32.18
session_info['date']                   	   	= datetime.now().strftime("%Y-%m-%d")
session_info['time']                   	   	= datetime.now().strftime('%H%M%S')
session_info['datetime']					= session_info['date'] + '_' + session_info['time']
session_info['basename']                  	= mouse_info['mouse_name'] + '_' + session_info['datetime']
session_info['box_name']             		= socket.gethostname()
session_info['dirname']  					= session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info['datetime']


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



