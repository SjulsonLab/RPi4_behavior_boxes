# session_info_headfixed.py

# put all of your mouse and session info in here

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
session_info["lick_threshold"]              = 2
# visual stimulus
session_info["visual_stimulus"]             = False
# session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
# session_info['vis_gratings']				= ['/home/pi/first_grating.dat',
# 											   '/home/pi/second_grating.dat']
# session_info['vis_raws']					= []

# task related information

session_info['config']	                    = 'headfixed_soyoun'
session_info['treadmill_setup'] = {}
session_info['treadmill_setup']['present']             = True
session_info['phase']             	= 1

if session_info['treadmill_setup']['present']:
    session_info['treadmill_setup']['distance_initiation'] = 1  # cm
    session_info['treadmill_setup']['distance_short'] = 3  # cm
    session_info['treadmill_setup']['distance_long'] = 5 # cm
else:
    session_info['treadmill_setup'] = None

session_info['error_repeat'] = True
if session_info['error_repeat']:
    session_info['error_max'] = 3

# condition setup
session_info['cue'] = ['sound', 'LED', 'sound+LED']
session_info['state'] = ['distance_short', 'distance_long']  # treadmill distance
session_info['choice'] = ['right', 'left']  # lick port
session_info['reward'] = ['small', 'large']  # reward size
session_info['reward_size'] = {'small': 5, 'large': 10}

if session_info['phase'] == 1:
    session_info['reward_size'] = {'small': 20, 'large': 20}

# define timeout during each condition
session_info['initiation_timeout'] = 120  # s
session_info['cue_timeout'] = 120
session_info['reward_timeout'] = 60
session_info["punishment_timeout"] = 1

# define block_duration and initial block to start the session
session_info['block_duration'] = 5  # each block has this amount of repetition
session_info['block_variety'] = 2
if session_info['block_variety'] > 1:
    session_info['initial_block'] = 1

# # allowing user defined initial_block and initial setup for conditions?
# task_information["initial_block"] = 1
#
# allowing consecutive repeated trial?
session_info['consecutive_control'] = True
if session_info['consecutive_control']:
    session_info['consecutive_max'] = 3