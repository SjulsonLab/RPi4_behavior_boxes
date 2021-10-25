# fake fake_session_info file (used for testing)

import collections, socket
from datetime import datetime

fake_session_info                                = collections.OrderedDict()
fake_session_info['mouse_name']                  = 'fakemouse01'
fake_session_info['basedir']                     = '/home/pi/fakedata'
fake_session_info['flipper_filename']            = '/home/pi/fakedata/flipper_timestamp'
fake_session_info['date']                        = datetime.now().strftime("%Y-%m-%d")
fake_session_info['time']                        = datetime.now().strftime('%H%M%S')
fake_session_info['datetime']                    = fake_session_info['date'] + '_' + fake_session_info['time']
fake_session_info['basename']                    = fake_session_info['mouse_name'] + '_' + fake_session_info['datetime']
fake_session_info['box_name']                    = socket.gethostname()
fake_session_info['dir_name']                    = fake_session_info['basedir'] + "/" + fake_session_info['mouse_name'] + "_" + fake_session_info['datetime']
# fake_session_info['config']                        = 'freely_moving_v1'
fake_session_info['config']                      = 'head_fixed_v1'
fake_session_info['timeout_length']              = 5  # in seconds
fake_session_info['reward_size']                 = 10  # in microliters

# visual stimulus
fake_session_info['gray_level']                  = 40  # the pixel value from 0-255 for the screen between stimuli
fake_session_info['vis_gratings']                = ['/home/pi/gratings/first_grating.dat', '/home/pi/gratings/second_grating.dat']
fake_session_info['vis_raws']                    = []
