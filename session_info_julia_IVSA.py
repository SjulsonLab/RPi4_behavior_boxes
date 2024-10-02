# session_info_julia_test_self_admin.py

import pysistence, collections
import socket

# Defining immutable mouse dict (once defined for a mouse, NEVER EDIT IT)
mouse_info = pysistence.make_dict({'mouse_name': 'test',
                 'fake_field': 'fake_info',
                 })

# Information for this session (user should edit this each session)
session_info                              	= collections.OrderedDict()
session_info['mouse_info']					= mouse_info
session_info['mouse_name']                 	= mouse_info['mouse_name']

session_info['file_basename'] = 'place_holder'

session_info['basedir']					  	= '/home/pi/buffer'
session_info['external_storage']            = '/mnt/hd'
session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'

# Mouse weight is entered here and read by the task file
session_info['weight']                	    = 32.18  # Modify this as needed

session_info['manual_date']					= '202x-xx-xx'
session_info['box_name']             		= socket.gethostname()

session_info['config']						= 'self_admin' 

session_info['max_trial_number']            = 100  # Safety precaution

# Behavior parameters
session_info['timeout_length']              = 20  # in seconds

# Added cath_fill for catheter fill duration
session_info['cath_fill']                   = 3    # in seconds, modify as needed for the task

# removed below for visual stim
# visual stimulus
# session_info["visual_stimulus"]             = False
# session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
# session_info['vis_gratings']				= ['/home/pi/first_grating.dat',
# 											   '/home/pi/second_grating.dat']
# session_info['vis_raws']					= []

# Task-related information
session_info['config']	                    = 'headfixed_self_admin'
session_info['treadmill_setup']             = {}
session_info['treadmill']                   = True
if session_info['treadmill']:
    session_info['treadmill_setup']['distance_initiation'] = 10  # cm
    session_info['treadmill_setup']['distance_cue'] = 25  # cm
else:
    session_info['treadmill_setup'] = None

session_info['error_repeat'] = True
if session_info['error_repeat']:
    session_info['error_max'] = 3
