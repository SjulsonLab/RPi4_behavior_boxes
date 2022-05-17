from gpiozero import Button, LED
import time

lick_entry = Button(5, pull_up=True)
led_indicator = LED(22)

while True:
    lick_entry.wait_for_press()
    print(str(time.time()) + ", The button was pressed!")
    led_indicator.on()
    lick_entry.wait_for_release()
    print("The button was released!")
    led_indicator.off()