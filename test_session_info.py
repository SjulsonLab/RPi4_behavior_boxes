# fake test_session_info file (used for testing)

import collections, socket
from datetime import datetime

test_session_info                                = collections.OrderedDict()
test_session_info['mouse_name']                  = 'testmouse'
test_session_info['basedir']                     = '/home/pi/video'
test_session_info['date']                        = datetime.now().strftime("%Y-%m-%d")
test_session_info['time']                        = datetime.now().strftime('%H%M%S')
test_session_info['datetime']                    = test_session_info['date'] + '_' + test_session_info['time']
test_session_info['basename']                    = test_session_info['mouse_name'] + '_' + test_session_info['datetime']
test_session_info['box_name']                    = socket.gethostname()
test_session_info['dir_name']                    = test_session_info['basedir'] + "/" + test_session_info['mouse_name'] + "_" + test_session_info['datetime']
# test_session_info['config']                        = 'freely_moving_v1'
test_session_info['config']                      = 'head_fixed_v1'
test_session_info['timeout_length']              = 5  # in seconds
test_session_info['reward_size']                 = 10  # in microliters

# visual stimulus
test_session_info['gray_level']                  = 40  # the pixel value from 0-255 for the screen between stimuli
test_session_info['vis_gratings']                = ['/home/pi/gratings/first_grating.grat', '/home/pi/gratings/second_grating.grat']
test_session_info['vis_raws']                    = []