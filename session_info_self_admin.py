# session_info_self_admin.py

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

session_info['file_basename'] = 'place_holder'

session_info['basedir']					  	= '/home/pi/buffer'
session_info['external_storage']            = '/mnt/hd'
session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'

session_info['weight']                	    = 32.18
session_info['manual_date']					= '202x-xx-xx'
session_info['box_name']             		= socket.gethostname()

# session_info['config']						= 'freely_moving_v1'
session_info['config']						= 'self_admin'

session_info['max_trial_number']            = 100

# behavior parameters
session_info['timeout_length']              = 5  # in seconds
session_info['reward_size']					= 10  # in microliters
session_info["lick_threshold"]              = 2
session_info['reward_time_delay']           = 20
# visual stimulus
session_info["visual_stimulus"]             = False
# session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
# session_info['vis_gratings']				= ['/home/pi/first_grating.dat',
# 											   '/home/pi/second_grating.dat']
# session_info['vis_raws']					= []

# task related information

session_info['config']	                    = 'headfixed_self_admin'
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
session_info["reward_pump"] = '3'
session_info['reward_size'] = 5

# define timeout during each condition
session_info['initiation_timeout'] = 120  # s

session_info['lever_press_interval'] = 1
session_info['ContextA_reward_probability'] = 1
session_info['ContextB_reward_probability'] = 1
session_info["ContextA_time"] = 300
session_info["ContextB_time"] = 300
session_info["ContextC_time"] = 150

#code below added for two action version of the context task
session_info["reward_pump1"] = '3' #update this in session_info
session_info['reward_pump2'] = '1' #update this in session_info
session_info["reward_size1"] = 1   #update this in session_info
session_info['reward_size2'] = 1   #update this in session_info