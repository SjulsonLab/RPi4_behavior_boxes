#!/usr/bin/env python3
"""
Standalone reward calibration for the GPIO19 solenoid.

The calibration delivers 100 rewards at each solenoid time, asks for the tube
weight before and after water collection, then plots microliters per drop.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import sleep


DEFAULT_SOLENOID_TIMES_S = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
DEFAULT_SOLENOID_TIMES_S = [0.05, 0.075, 0.1, 0.125] # this range should be sufficient for box 131

DEFAULT_REWARD_COUNT = 100
DEFAULT_OFF_TIME_S = 0.01
DEFAULT_PULSE_COUNT = 6
DEFAULT_INTER_REWARD_INTERVAL_S = 0.5
DEFAULT_PUMP_PIN = 19


@dataclass
class CalibrationResult:
    """
    Store one completed solenoid calibration measurement.

    Parameters
    ----------
    solenoid_time_s : float
        Solenoid open time for each pulse, in seconds.
    initial_weight_g : float
        Weight of the empty collection tube/container, in grams.
    final_weight_g : float
        Weight of the tube/container plus collected water, in grams.
    reward_count : int
        Number of rewards delivered; no shape or axis conventions apply.
    reward_size_ul_per_drop : float
        Mean water volume per reward/drop, in microliters.

    Returns
    -------
    CalibrationResult
        Dataclass instance containing the calibration measurement.
    """

    solenoid_time_s: float
    initial_weight_g: float
    final_weight_g: float
    reward_count: int
    reward_size_ul_per_drop: float


class GpiozeroPulsePump:
    """
    Deliver GPIO19 rewards using the same six-pulse pattern as the task code.

    Parameters
    ----------
    pin : int
        Broadcom GPIO pin number for the reward solenoid; GPIO19 is the current
        pump-1 reward pin.

    Returns
    -------
    GpiozeroPulsePump
        Pump wrapper with ``reward``, ``off``, and ``close`` methods.
    """

    def __init__(self, pin=DEFAULT_PUMP_PIN):
        """
        Initialize the GPIO output pin.

        Parameters
        ----------
        pin : int
            Broadcom GPIO pin number for the reward solenoid.

        Returns
        -------
        None
            The GPIO output is stored on this object.
        """
        from gpiozero import LED

        self._led = LED(pin)

    def reward(self, which_pump, on_time_s, off_time_s, pulse_count):
        """
        Deliver one reward as a blocking pulse train.

        Parameters
        ----------
        which_pump : str
            Pump identifier. Only "1" is valid here, matching pump 1/GPIO19.
        on_time_s : float
            Solenoid open time for each pulse, in seconds.
        off_time_s : float
            Time between solenoid pulses, in seconds.
        pulse_count : int
            Number of pulses per reward; the current behavior task uses 6.

        Returns
        -------
        None
            The solenoid pulse train is delivered before the method returns.
        """
        if which_pump != "1":
            raise ValueError("calibration.py only supports pump '1' on GPIO19")

        self._led.blink(on_time_s, off_time_s, pulse_count, background=False)

    def off(self):
        """
        Turn the solenoid output off.

        Parameters
        ----------
        None
            This method takes no inputs.

        Returns
        -------
        None
            The GPIO output is set low.
        """
        self._led.off()

    def close(self):
        """
        Release the GPIO output.

        Parameters
        ----------
        None
            This method takes no inputs.

        Returns
        -------
        None
            The GPIO device is closed.
        """
        self._led.close()


def calculate_reward_size_ul_per_drop(initial_weight_g, final_weight_g, reward_count):
    """
    Convert collected water weight into mean reward size.

    Parameters
    ----------
    initial_weight_g : float
        Tube/container weight before water collection, in grams.
    final_weight_g : float
        Tube/container weight after water collection, in grams.
    reward_count : int
        Number of rewards delivered. Must be greater than zero.

    Returns
    -------
    float
        Mean reward size, in microliters per drop/reward, assuming water is
        approximately 1 gram per milliliter.
    """
    if reward_count <= 0:
        raise ValueError("reward_count must be greater than zero")
    if final_weight_g < initial_weight_g:
        raise ValueError("final_weight_g must be greater than or equal to initial_weight_g")

    collected_water_g = final_weight_g - initial_weight_g
    collected_water_ul = collected_water_g * 1000.0
    return collected_water_ul / reward_count


def deliver_rewards(
    pump,
    solenoid_time_s,
    reward_count=DEFAULT_REWARD_COUNT,
    off_time_s=DEFAULT_OFF_TIME_S,
    pulse_count=DEFAULT_PULSE_COUNT,
    inter_reward_interval_s=DEFAULT_INTER_REWARD_INTERVAL_S,
    sleep_fn=sleep,
):
    """
    Deliver repeated rewards for one solenoid timing condition.

    Parameters
    ----------
    pump : object
        Object with ``reward(which_pump, on_time_s, off_time_s, pulse_count)``.
    solenoid_time_s : float
        Solenoid open time for each pulse, in seconds.
    reward_count : int
        Number of rewards to deliver. Scalar count, no axis conventions.
    off_time_s : float
        Time between pulses within a reward, in seconds.
    pulse_count : int
        Number of pulses per reward.
    inter_reward_interval_s : float
        Waiting time after each reward pulse train, in seconds.
    sleep_fn : callable
        Function accepting seconds as a float; used to wait between rewards.

    Returns
    -------
    None
        Rewards are delivered through the pump object.
    """
    for reward_index in range(reward_count):
        print(f"reward {reward_index + 1}/{reward_count}")
        pump.reward("1", solenoid_time_s, off_time_s, pulse_count)
        if inter_reward_interval_s > 0:
            sleep_fn(inter_reward_interval_s)


def read_float(prompt):
    """
    Read a floating-point number from the terminal.

    Parameters
    ----------
    prompt : str
        User-facing prompt text.

    Returns
    -------
    float
        Parsed scalar value entered by the user.
    """
    while True:
        raw_value = input(prompt)
        try:
            return float(raw_value)
        except ValueError:
            print("Please enter a number, for example 2.345")


def run_calibration(
    pump,
    solenoid_times_s=DEFAULT_SOLENOID_TIMES_S,
    reward_count=DEFAULT_REWARD_COUNT,
    off_time_s=DEFAULT_OFF_TIME_S,
    pulse_count=DEFAULT_PULSE_COUNT,
    inter_reward_interval_s=DEFAULT_INTER_REWARD_INTERVAL_S,
):
    """
    Run the full interactive calibration sequence.

    Parameters
    ----------
    pump : object
        Object with ``reward(which_pump, on_time_s, off_time_s, pulse_count)``.
    solenoid_times_s : list of float
        Solenoid open times to test, in seconds. The list is one-dimensional.
    reward_count : int
        Number of rewards delivered at each solenoid time.
    off_time_s : float
        Time between pulses within a reward, in seconds.
    pulse_count : int
        Number of pulses per reward.
    inter_reward_interval_s : float
        Waiting time after each reward pulse train, in seconds.

    Returns
    -------
    list of CalibrationResult
        One result per solenoid time, in the same order as ``solenoid_times_s``.
    """
    results = []

    for solenoid_time_s in solenoid_times_s:
        print("\n" + "=" * 60)
        print(f"Solenoid time: {solenoid_time_s:.1f} s")
        initial_weight_g = read_float("Enter starting tube/container weight in grams: ")
        input(f"Press Enter to deliver {reward_count} rewards at {solenoid_time_s:.1f} s. ")

        deliver_rewards(
            pump=pump,
            solenoid_time_s=solenoid_time_s,
            reward_count=reward_count,
            off_time_s=off_time_s,
            pulse_count=pulse_count,
            inter_reward_interval_s=inter_reward_interval_s,
        )

        print("Done delivering rewards. Weigh the tube/container with water.")
        final_weight_g = read_float("Enter final tube/container weight in grams: ")
        reward_size_ul = calculate_reward_size_ul_per_drop(
            initial_weight_g=initial_weight_g,
            final_weight_g=final_weight_g,
            reward_count=reward_count,
        )
        print(f"Reward size = {reward_size_ul:.3f} uL/drop")

        results.append(
            CalibrationResult(
                solenoid_time_s=solenoid_time_s,
                initial_weight_g=initial_weight_g,
                final_weight_g=final_weight_g,
                reward_count=reward_count,
                reward_size_ul_per_drop=reward_size_ul,
            )
        )

    return results


def write_results_csv(results, output_path):
    """
    Save calibration measurements to a CSV file.

    Parameters
    ----------
    results : list of CalibrationResult
        One-dimensional list of calibration measurements.
    output_path : str or pathlib.Path
        Destination CSV path.

    Returns
    -------
    pathlib.Path
        Path to the written CSV file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "solenoid_time_s",
        "initial_weight_g",
        "final_weight_g",
        "reward_count",
        "reward_size_ul_per_drop",
    ]
    with output_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "solenoid_time_s": result.solenoid_time_s,
                    "initial_weight_g": result.initial_weight_g,
                    "final_weight_g": result.final_weight_g,
                    "reward_count": result.reward_count,
                    "reward_size_ul_per_drop": result.reward_size_ul_per_drop,
                }
            )

    return output_path


def plot_calibration_curve(results, output_path):
    """
    Plot reward size as a function of solenoid time.

    Parameters
    ----------
    results : list of CalibrationResult
        One-dimensional list of calibration measurements.
    output_path : str or pathlib.Path
        Destination PNG path.

    Returns
    -------
    pathlib.Path
        Path to the written PNG plot.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(output_path.parent / ".matplotlib_cache"))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    solenoid_times_s = [result.solenoid_time_s for result in results]
    reward_sizes_ul = [result.reward_size_ul_per_drop for result in results]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(solenoid_times_s, reward_sizes_ul, marker="o", color="black")
    ax.set_xlabel("Solenoid time (s)")
    ax.set_ylabel("Reward size (uL/drop)")
    ax.set_title("Reward calibration")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    return output_path


def build_argument_parser():
    """
    Build the command-line argument parser.

    Parameters
    ----------
    None
        This function takes no inputs.

    Returns
    -------
    argparse.ArgumentParser
        Parser for calibration runtime settings.
    """
    parser = argparse.ArgumentParser(description="Calibrate GPIO19 reward size.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "calibration_results",
        help="Directory for the CSV and PNG outputs.",
    )
    parser.add_argument(
        "--reward-count",
        type=int,
        default=DEFAULT_REWARD_COUNT,
        help="Number of rewards delivered at each solenoid time.",
    )
    parser.add_argument(
        "--inter-reward-interval",
        type=float,
        default=DEFAULT_INTER_REWARD_INTERVAL_S,
        help="Seconds to wait after each reward pulse train.",
    )
    return parser


def main():
    """
    Run standalone calibration from the command line.

    Parameters
    ----------
    None
        Runtime settings are read from command-line arguments and terminal input.

    Returns
    -------
    None
        Calibration results are saved as CSV and PNG files.
    """
    parser = build_argument_parser()
    args = parser.parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.output_dir / f"reward_calibration_{timestamp}.csv"
    plot_path = args.output_dir / f"reward_calibration_{timestamp}.png"

    pump = GpiozeroPulsePump()
    try:
        results = run_calibration(
            pump=pump,
            reward_count=args.reward_count,
            inter_reward_interval_s=args.inter_reward_interval,
        )
        written_csv_path = write_results_csv(results, csv_path)
        written_plot_path = plot_calibration_curve(results, plot_path)
    except KeyboardInterrupt:
        print("\nCalibration stopped by user.")
        return
    finally:
        pump.off()
        pump.close()

    print("\nCalibration complete.")
    print(f"Saved CSV: {written_csv_path}")
    print(f"Saved plot: {written_plot_path}")


if __name__ == "__main__":
    main()
