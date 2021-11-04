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
fale_session_info                              	= collections.OrderedDict()
fale_session_info['mouse_info']					= mouse_info
fale_session_info['mouse_name']                 	= mouse_info['mouse_name']
#fale_session_info['trainingPhase']             	= 4
fale_session_info['basedir']					  	= '/home/pi/buffer'
fale_session_info['external_storage']            = '/mnt/hd'
# fale_session_info['flipper_filename']            = '/home/pi/buffer/flipper_timestamp'
# for actual data save to this dir:
#fale_session_info['basedir']					  	= '/home/pi/video'
fale_session_info['weight']                	    = 32.18
fale_session_info['manual_date']					= '2021-09-14'
fale_session_info['box_name']             		= socket.gethostname()

# fale_session_info['config']						= 'freely_moving_v1'
fale_session_info['config']						= 'head_fixed_v1'

# behavior parameters
fale_session_info['timeout_length']              = 5  # in seconds
fale_session_info['reward_size']					= 10  # in microliters

# visual stimulus
fale_session_info['gray_level']					= 40  # the pixel value from 0-255 for the screen between stimuli
fale_session_info['vis_gratings']				= ['/home/pi/gratings/first_grating.dat',
											   '/home/pi/gratings/second_grating.dat']
fale_session_info['vis_raws']					= []

