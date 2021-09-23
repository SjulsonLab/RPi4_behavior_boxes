from FlipperOutput import FlipperOutput
from fake_session_info import fake_session_info
from time import sleep

with FlipperOutput(fake_session_info, pin=22) as flip_box:
    try:
        flip_box.flip()
        sleep(10)
        flip_box.close()
    except KeyboardInterrupt:
        flip_box.close()
        print("Closing the output.")
    except Exception as e:
        flip_box.close()
        print("Closing the output.")
        print(e)