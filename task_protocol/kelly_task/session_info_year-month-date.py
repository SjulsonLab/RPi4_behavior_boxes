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
session_info = collections.OrderedDict()
session_info['mouse_info'] = mouse_info
session_info['mouse_name'] = mouse_info['mouse_name']
# session_info['trainingPhase']             	= 4
session_info['basedir'] = '/home/pi/buffer'
session_info['external_storage'] = '/mnt/hd'
session_info['flipper_filename'] = '/home/pi/buffer/flipper_timestamp'
# for actual data save to this dir:
# session_info['basedir']					  	= '/home/pi/video'
session_info['weight'] = 32.18
session_info['manual_date'] = '202x-xx-xx'
session_info['box_name'] = socket.gethostname()

# session_info['config']						= 'freely_moving_v1'
session_info['experiment_setup'] = 'head_fixed'
session_info['treadmill'] = True
session_info['treadmill_setup'] = {}
if session_info['treadmill']:
    session_info['treadmill_setup']['distance_initiation'] = 5  # cm
    session_info['treadmill_setup']['distance_short'] = 7  # cm
    session_info['treadmill_setup']['distance_long'] = 30  # cm

# behavior parameters
# define timeout during each condition
session_info['initiation_timeout'] = 120  # s
session_info['cue_timeout'] = 120
session_info['reward_timeout'] = 5
session_info["reward_wait"] = 5
session_info["punishment_timeout"] = 0

# error repeat
session_info['error_repeat'] = True
if session_info['error_repeat']:
    session_info['error_repeat_max'] = 3

# reward parameters
# session_info['reward_size']					= 10  # in microliters
session_info['reward_size'] = {'small': 5, 'large': 10}  # in microliters

# visual stimulus
session_info["visual_stimulus"] = False
# session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
# session_info['vis_gratings']				= ['/home/pi/gratings/first_grating.dat',
# 											   '/home/pi/gratings/second_grating.dat']
session_info['vis_gratings'] = []
session_info['vis_raws'] = []

# define block_duration and initial block to start the session
session_info['block_duration'] = 2  # each block has this amount of repetition
session_info['block_variety'] = 2
if session_info['block_variety'] > 1:
    initial_block = 1
