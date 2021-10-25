# pump_debug.py: it's for testing the pump class and the pump itself
from behavbox import Pump
from fake_session_info import fake_session_info

pump = Pump()
session_info = fake_session_info
pump.reward("left", session_info["reward_size"])