# put all of your mouse and session info in here
import random
from datetime import datetime
import os
import pysistence, collections
import socket


# defining immutable mouse dict (once defined for a mouse, NEVER EDIT IT)
mouse_info = pysistence.make_dict({'mouse_name': 'test',
                 'fake_field': 'fake_info',
                 })

# Information for this session (the user should edit this each session)
session_info                              	= collections.OrderedDict()
session_info['mouse_info']					= mouse_info
session_info['mouse_name']                 	= mouse_info['mouse_name']
#session_info['trainingPhase']             	= 4
session_info['basedir']					  	= '/home/pi/buffer'
session_info['external_storage']            = '/mnt/hd'
session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'
# for actual data save to this dir:
#session_info['basedir']					  	= '/home/pi/video'
session_info['weight']                	    = 32.18
session_info['manual_date']					= '202x-xx-xx'
session_info['box_name']             		= socket.gethostname()

# session_info['config']						= 'freely_moving_v1'
session_info['config']						= 'head_fixed_v1'

# behavior parameters
session_info['timeout_length']              = 5  # in seconds
session_info['reward_size']					= 10  # in microliters

# visual stimulus
session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
session_info['vis_gratings']				= ['/home/pi/first_grating.dat', 
											   '/home/pi/second_grating.dat']
session_info['vis_raws']					= []

# treadmill
session_info['treadmill']                   = True
if session_info['treadmill'] == True:
    session_info['treadmill_task']                        = 'headfixed_reinforcement_learning'
    session_info['phase_number']                          = 4
    if session_info['phase_number'] == 4: # 4 is final stage
        session_info['block_duration'] = 50
        session_info['initial_state'] = 'sound_long' # sound prompt for long distance => high reward;
                                                    # short distance => small reward; reverse for cue light
        if session_info['initial_state'] == False:
            if random.random() < 0.5:
                session_info['initial_state'] = 'sound_long'
            else:
                session_info['initial_state'] = 'sound_short' # sound prompt for short distance => low reward;
                                                            # short distance => high reward; reverse for cue light