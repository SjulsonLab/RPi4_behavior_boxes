# pump_debug.py: it's for testing the pump class and the pump itself
import sys
import time
# updated with reorganization (on 7/11/2023)
import sys
sys.path.insert(0,'/home/pi/RPi4_behavior_boxes/essential')
from behavbox import Pump
# from fake_session_info import fake_session_info
side = str(sys.argv[1])
pump = Pump()
# session_info = fake_session_info
pump.reward(side, 20)
time.sleep(1)