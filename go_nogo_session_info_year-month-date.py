# put all of your mouse and session info in here

from datetime import datetime
import os
import pysistence, collections
import socket


# defining immutable mouse dict (once defined for a mouse, NEVER EDIT IT)
mouse_info = pysistence.make_dict({'mouse_name': 'DT000',
                 })

# Information for this session (the user should edit this each session)
session_info                              	= collections.OrderedDict()
session_info['mouse_info']					= mouse_info
session_info['mouse_name']                 	= mouse_info['mouse_name']
session_info['training_phase']             	= 1
session_info['basedir']					  	= '/home/pi/buffer'
session_info['external_storage']            = '/mnt/hd'
# session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'
# for actual data save to this dir:
#session_info['basedir']					  	= '/home/pi/video'
session_info['weight']                	    = 32.18
session_info['manual_date']					= '2021-11-19'
session_info['box_name']             		= socket.gethostname()

# session_info['config']						= 'freely_moving_v1'
session_info['config']						= 'head_fixed_v1'

# behavior parameters
session_info['number_of_trials']            = 500  # total number of phase 2 trials
session_info['number_of_phase1_trials']     = 100
session_info['hit_criterion']               = 0.85  # 85% hit rate!
session_info['lockout_length']              = 2  # in seconds
session_info['vacuum_length']               = 0.5  # in seconds
session_info['reward_available_length']     = 1  # in seconds
session_info['lick_count_length']           = 1  # in seconds
session_info['reward_size']					= 11  # in microliters
session_info['reward_duration']             = 0.01
session_info['normal_iti_length']           = 3 - session_info['vacuum_length']
session_info['punishment_iti_length']       = 6.5 - session_info['vacuum_length']

# visual stimulus
session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
session_info['vis_gratings_go']				= ['/home/pi/gratings/first_grating_go.dat']
session_info['vis_gratings_nogo']           = ['/home/pi.gratings/first_grating_nogo.dat']
session_info['vis_raws']					= []

