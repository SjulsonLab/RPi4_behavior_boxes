import RPi.GPIO as GPIO
import time
import threading
import concurrent.futures

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)

# Define the GPIO pin number
pin_number = 4

# Set up the GPIO pin as an input
# GPIO.setup(pin_number, GPIO.IN)
GPIO.setup(pin_number, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(pin_flipper, GPIO.BOTH, bouncetime=100)
GPIO.add_event_callback(pin_number, flipper_timestamps_detect)
previous_state = GPIO.input(pin_number)
print("Start state is {}".format(previous_state))

state_change = threading.Event()

def check_input_change(previous_state):
    current_state = GPIO.input(pin_number)
    if current_state != previous_state:
        if current_state == GPIO.HIGH:
            print("GPIO pin is HIGH")
        else:
            print("GPIO pin is LOW")
        previous_state = current_state
    return current_state


def flipper_timestamps_detect():
    input_state = GPIO.input(pin_number)
    GPIO.remove_event_detect(pin_number)
    print(input_state, time.time())
    GPIO.add_event_detect(pin_flipper, GPIO.BOTH, bouncetime=BOUNCETIME)


try:
    while True:
        # Read the current state of the GPIO pin
        current_state = GPIO.input(pin_number)

        # Check if the state has changed
        if current_state != previous_state:
            if current_state == GPIO.HIGH:
                print("GPIO pin is HIGH")
            else:
                print("GPIO pin is LOW")

            # Update the previous state
            previous_state = current_state

        # Wait for 20 milliseconds before checking again
        time.sleep(0.02)

except KeyboardInterrupt:
    # Clean up GPIO settings before exiting
    GPIO.cleanup()

