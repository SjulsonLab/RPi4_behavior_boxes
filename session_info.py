# put all of your mouse and session info in here

import pysistence, collections
import socket
from datetime import datetime


### PARAMETERS - Rig and defaults (should not change between sessions) ###

# defining immutable mouse dict (once defined for a mouse, NEVER EDIT IT)
mouse_info = pysistence.make_dict({'mouse_name': 'TM001',
                                   'fake_field': 'fake_info',
                                   })

# Parameters: mouse, session type

# Information for this session (the user should edit this each session)
session_info                              	= collections.OrderedDict()
session_info['mouse_info']					= mouse_info
session_info['mouse_name']                 	= mouse_info['mouse_name']

session_info['weight']                	    = 30  # in grams
session_info['date']					= datetime.now().strftime("%Y-%m-%d")  # for example, '2023-09-28'
session_info['task_config']				    = 'alternating_latent'

# behavior parameters - ideally set these to a default for each session type, which is adjustable
session_info['max_trial_number']            = 100
session_info['timeout_length']              = 5  # in seconds
session_info['reward_size']					= 10  # in microliters
session_info["lick_threshold"]              = 2
session_info['reward_time_delay']           = 20

session_info['initiation_timeout'] = 120  # s

session_info['entry_interval'] = 1  # this is the one that delays between choices
session_info['timeout_time'] = 3
session_info['ContextA_reward_probability'] = 1
session_info['ContextB_reward_probability'] = 1

session_info['correct_reward_probability'] = 1
session_info['incorrect_reward_probability'] = 0

session_info["ContextA_time"] = 30  # todo - revise this or make adjustable by mouse performance
session_info["ContextB_time"] = 30
session_info["ContextC_time"] = 30

# Reward pump parameters
session_info["reward_pump1"] = '2'
session_info['reward_pump2'] = '1'

session_info['reward_size_large'] = [3, 3]
session_info['reward_size_small'] = [0, 0]
session_info['errors_to_reward_delivery'] = 5
session_info['key_reward_amount'] = 3

# Parameters - file saving
session_info['file_basename']               = 'place_holder'
session_info['basedir']					  	= '/home/pi/buffer'
session_info['external_storage']            = '/mnt/hd'
session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'

# Parameters - box and rig
session_info['box_name']             		= socket.gethostname()

session_info["visual_stimulus"]             = False
session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
session_info['vis_gratings']				= ['/home/pi/gratings/context_a.dat',
                                               '/home/pi/gratings/context_b.dat']
session_info['vis_raws']					= []

session_info['treadmill_setup']             = {}
session_info['treadmill']                   = True


if session_info['treadmill']:
    session_info['treadmill_setup']['distance_initiation'] = 10  # cm
    session_info['treadmill_setup']['distance_cue'] = 25  # cm
else:
    session_info['treadmill_setup'] = None


### DEPRECATED / NOT CURRENTLY IN USE ###
session_info['LED_duration'] = 3

session_info['error_repeat'] = True
if session_info['error_repeat']:
    session_info['error_max'] = 3

session_info["reward_pump"] = '2'
session_info['reward_size'] = 1
