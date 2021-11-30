# put all of your mouse and session info in here

from datetime import datetime
import os
import pysistence, collections
import socket


# defining immutable mouse dict (once defined for a mouse, NEVER EDIT IT)
mouse_info = pysistence.make_dict({'mouse_name': 'DT000_phase0',
                 })

# Information for this session (the user should edit this each session)
session_info                              	= collections.OrderedDict()
session_info['mouse_info']					= mouse_info
session_info['mouse_name']                 	= mouse_info['mouse_name']
#session_info['trainingPhase']             	= 4
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
session_info['delay_time']                  = 1  # delay time between astim and vstim (in s)
session_info['number_of_trials']            = 300  # total number of trials
session_info['init_length']                 = 1  # in seconds
session_info['lockout_length']              = 0.2  # in seconds
session_info['vacuum_length']               = 0.1  # in seconds
session_info['trial_length']                = 3  # length of trial after vstim starts
session_info['time_for_plotting']           = 0  # based on the readout when running the task
session_info['reward_available_length']     = session_info['trial_length'] - session_info['lockout_length']
session_info['reward_size']					= 10  # in microliters
session_info['iti_length']                  = 3 - session_info['vacuum_length'] - session_info['time_for_plotting']
#  2.5s for ITI because plotting takes 0.8s-1.2s
session_info['normal_iti_length']           = 2 - session_info['vacuum_length'] - session_info['time_for_plotting']
session_info['punishment_iti_length']       = 5.5 - session_info['vacuum_length'] - session_info['time_for_plotting']

# visual stimulus
session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
session_info['vis_gratings']				= ['/home/pi/gratings/first_grating_ssrt.dat']
session_info['vis_raws']					= []

