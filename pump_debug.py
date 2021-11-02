# pump_debug.py: it's for testing the pump class and the pump itself
import sys

from behavbox import Pump
# from fake_session_info import fake_session_info
side = str(sys.argv[1])
pump = Pump()
# session_info = fake_session_info
pump.reward(side, 20)