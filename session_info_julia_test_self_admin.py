# session_info_julia_test_self_admin.py

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

# session_info['config']						= 'freely_moving_v1' #??
session_info['config']						= 'self_admin' #??

session_info['max_trial_number']            = 100 #safetyprecaution

# behavior parameters
session_info['timeout_length']              = 20  # in seconds


#removed below for visual stim
# visual stimulus
#session_info["visual_stimulus"]             = False
# session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
# session_info['vis_gratings']				= ['/home/pi/first_grating.dat',
# 											   '/home/pi/second_grating.dat']
# session_info['vis_raws']					= []

# task related information

session_info['config']	                    = 'headfixed_self_admin'
session_info['treadmill_setup'] = {}
session_info['treadmill']             = True
#edit any of the below? anything for LED/tone or not in this doc?
if session_info['treadmill']:
    session_info['treadmill_setup']['distance_initiation'] = 10  # cm
    session_info['treadmill_setup']['distance_cue'] = 25  # cm
else:
    session_info['treadmill_setup'] = None

session_info['error_repeat'] = True
if session_info['error_repeat']:
    session_info['error_max'] = 3