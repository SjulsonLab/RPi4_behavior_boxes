from FlipperOutput import FlipperOutput
from fake_session_info import fake_session_info
import sleep

flip_box = FlipperOutput(fake_session_info, pin = 22)

flip_box.flip()

sleep(10)

flip_box.off()
