from FlipperOutput import FlipperOutput
from fake_session_info import fake_session_info
from time import sleep
import sys

# def signal_handler(signum):
#     print("SIGINT detected")
#     FlipperOutput.close()
#     print('Closing the output.')
#     sys.exit(0)
#
# signal.signal(signal.SIGINT, signal_handler)

with FlipperOutput(fake_session_info, pin=4) as flip_box:
    try:
        flip_box.flip()
        sleep(30)
        flip_box.close()
    except KeyboardInterrupt:
        print("try to interrupt")
        flip_box.close()
        print("Closing the output.")
    except Exception as e:
        print("Exception!")
        flip_box.close()
        print("Closing the output.")
        print(e)
