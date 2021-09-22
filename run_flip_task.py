from FlipperOutput import FlipperOutput
from fake_session_info import fake_session_info
from time import sleep

flip_box = FlipperOutput(fake_session_info, pin = 22)

flip_box.flip()

sleep(20)

flip_box.flipper_stop()