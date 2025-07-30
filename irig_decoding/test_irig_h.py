import irig_decoding.irig_h_gpio as irig
import time

sender = irig.IrigHSender(sending_gpio_pin=6)

try:
    sender.start()
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('keyboard interrupt recieved. stopping...')
finally:
    sender.finish()