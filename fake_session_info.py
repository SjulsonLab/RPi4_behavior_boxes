# put all of your mouse and session info in here

from datetime import datetime
import os
import pysistence, collections
import socket


# defining immutable mouse dict (once defined for a mouse, NEVER EDIT IT)
mouse_info = pysistence.make_dict({'mouse_name': 'test_pump',
                 'fake_field': 'fake_info',
                 })

# Information for this session (the user should edit this each session)
fake_session_info                              	= collections.OrderedDict()
fake_session_info['mouse_info']					= mouse_info
fake_session_info['mouse_name']                 	= mouse_info['mouse_name']
#fake_session_info['trainingPhase']             	= 4
fake_session_info['basedir']					  	= '/home/pi/buffer'
fake_session_info['external_storage']            = '/mnt/hd'
# fake_session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'
# for actual data save to this dir:
#fake_session_info['basedir']					  	= '/home/pi/video'
fake_session_info['weight']                	    = 32.18
fake_session_info['manual_date']					= '2021-09-14'
fake_session_info['box_name']             		= socket.gethostname()

# fake_session_info['config']						= 'freely_moving_v1'
fake_session_info['config']						= 'head_fixed_v1'

# behavior parameters
fake_session_info['timeout_length']              = 5  # in seconds
fake_session_info['reward_size']					= 10  # in microliters

# visual stimulus
fake_session_info['visual_stimulus']            = False
fake_session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
fake_session_info['vis_gratings']				= ['/home/pi/gratings/first_grating.dat',
											   '/home/pi/gratings/second_grating.dat']
fake_session_info['vis_raws']					= []

