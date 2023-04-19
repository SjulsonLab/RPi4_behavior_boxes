# session_info_walk.py

# put all of your mouse and session info in here

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

session_info['basedir']					  	= '/home/pi/buffer'
session_info['external_storage']            = '/mnt/hd'
session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'

session_info['weight']                	    = 32.18
session_info['manual_date']					= '202x-xx-xx'
session_info['box_name']             		= socket.gethostname()

# session_info['config']						= 'freely_moving_v1'
session_info['config']						= 'head_fixed_walk'

# behavior parameters
session_info['timeout_length']              = 5  # in seconds
session_info['reward_size']					= 10  # in microliters
session_info["lick_threshold"]              = 2
# visual stimulus
session_info["visual_stimulus"]             = False
# session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
# session_info['vis_gratings']				= ['/home/pi/first_grating.dat',
# 											   '/home/pi/second_grating.dat']
# session_info['vis_raws']					= []

# task related information

session_info['config']	                    = 'headfixed_walk'
session_info['treadmill_setup'] = {}
session_info['treadmill']             = True

if session_info['treadmill']:
    session_info['treadmill_setup']['distance_initiation'] = 10  # cm
    session_info['treadmill_setup']['distance_cue'] = 25  # cm
else:
    session_info['treadmill_setup'] = None

session_info['error_repeat'] = True
if session_info['error_repeat']:
    session_info['error_max'] = 3

# condition setup
session_info['cue'] = ['sound', 'LED', 'sound+LED']
session_info['reward_size'] = 5
session_info['air_duration'] = 0
session_info["vacuum_duration"] = 1

# solenoid valve liear fit coefficient for each pump
session_info["calibration_coefficient"]['1'] = [-0.30445602, 0.22461195, -0.00108027]  # highest power first
session_info["calibration_coefficient"]['2'] = [2.66288610e-02, 1.92493509e-01, -6.65082046e-05]
session_info["calibration_coefficient"]['3'] = [0.07929563, 0.20568105, -0.0013433]
session_info["calibration_coefficient"]['4'] = [-0.02619048, 0.21173333, -0.00135971]

# define timeout during each condition
session_info['initiation_timeout'] = 120  # s
session_info['cue_timeout'] = 120
session_info['reward_timeout'] = 60
session_info["punishment_timeout"] = 1
