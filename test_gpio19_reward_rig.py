#!/usr/bin/env python3
"""
Standalone GPIO19 solenoid/reward test for the rig.

Run on the Raspberry Pi with:
    python3 test_gpio19_reward_rig.py

Purpose:
1. Confirm GPIO19 can deliver water with clean on/off pulses.
2. Find the shortest pulse that reliably gives a drop.
3. Compare direct pulses against gpiozero blink-style pulses.

This script does NOT import your task code.
It only uses gpiozero LED(19), like your manual flush test.
"""

from gpiozero import LED
from time import sleep

PIN = 19
pump = LED(PIN)


def wait_for_enter(message):
    input("\n" + message + "\nPress Enter to continue, or Ctrl+C to stop. ")


def direct_pulse_test(on_time, n_pulses=10, inter_pulse_interval=1.0):
    print(f"\nDIRECT PULSE TEST: {n_pulses} pulses, ON={on_time}s, interval={inter_pulse_interval}s")
    for i in range(n_pulses):
        print(f"pulse {i + 1}/{n_pulses}")
        pump.on()
        sleep(on_time)
        pump.off()
        sleep(inter_pulse_interval)
    pump.off()


def direct_100_reward_test(on_time=0.1, inter_reward_interval=1.0):
    print(f"\n100-REWARD DIRECT TEST: ON={on_time}s, interval={inter_reward_interval}s")
    for i in range(100):
        print(f"reward {i + 1}/100")
        pump.on()
        sleep(on_time)
        pump.off()
        sleep(inter_reward_interval)
    pump.off()


def blink_train_test(on_time, off_time=0.01, numtimes=6, n_rewards=10, inter_reward_interval=0.5):
    print(
        f"\nBLINK TRAIN TEST: {n_rewards} rewards, "
        f"ON={on_time}s, OFF={off_time}s, numtimes={numtimes}, interval={inter_reward_interval}s"
    )
    for i in range(n_rewards):
        print(f"reward {i + 1}/{n_rewards}")
        # background=False is intentional: wait until the 6-pulse train finishes.
        pump.blink(on_time, off_time, numtimes, background=False)
        sleep(inter_reward_interval)
    pump.off()


def cleanup():
    pump.off()
    pump.close()


try:
    print("GPIO19 reward/solenoid standalone test")
    print("This uses gpiozero LED(19), same as your manual flush.")

    wait_for_enter("Step 1: 2-second flush test. Water should flow continuously.")
    pump.on()
    sleep(2.0)
    pump.off()
    print("Flush test done.")

    wait_for_enter("Step 2: 10 clean direct pulses at 100 ms. You should see drops.")
    direct_pulse_test(on_time=0.1, n_pulses=10, inter_pulse_interval=1.0)

    wait_for_enter("Step 3: pulse threshold test, from long to short.")
    for pulse in [0.2, 0.1, 0.08, 0.05, 0.03, 0.02, 0.01]:
        wait_for_enter(f"Testing {pulse}s ON pulses, 5 pulses total.")
        direct_pulse_test(on_time=pulse, n_pulses=5, inter_pulse_interval=1.0)

    wait_for_enter("Step 4: original-style 6-pulse blink train, blocking mode. Start with 30 ms ON.")
    blink_train_test(on_time=0.03, off_time=0.01, numtimes=6, n_rewards=10, inter_reward_interval=0.5)

    wait_for_enter("Step 5: original-style 6-pulse blink train, blocking mode. Now 100 ms ON.")
    blink_train_test(on_time=0.1, off_time=0.01, numtimes=6, n_rewards=10, inter_reward_interval=0.5)

    wait_for_enter("Step 6: full 100-reward direct calibration at 100 ms ON.")
    direct_100_reward_test(on_time=0.1, inter_reward_interval=1.0)

    print("\nAll tests complete. GPIO19 is OFF.")

except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    cleanup()
