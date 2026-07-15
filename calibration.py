#!/usr/bin/env python3
"""
Standalone reward calibration for the GPIO19 solenoid.

The calibration delivers repeated rewards at each selected solenoid time, asks
for the tube weight before and after water collection, calculates microliters
per drop, and estimates the solenoid time that should produce a 3 uL reward.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import sleep
from typing import Sequence


# This range should be sufficient for box 131.
DEFAULT_SOLENOID_TIMES_S = [0.05, 0.075, 0.1, 0.125]
DEFAULT_REWARD_COUNT = 100
DEFAULT_OFF_TIME_S = 0.01
DEFAULT_PULSE_COUNT = 6
DEFAULT_INTER_REWARD_INTERVAL_S = 0.5
DEFAULT_PUMP_PIN = 19
DEFAULT_TARGET_REWARD_SIZE_UL = 3.0
DEFAULT_MANUAL_MEASUREMENT_COUNT = 5


@dataclass(frozen=True)
class CalibrationResult:
    """Store one completed solenoid calibration measurement."""

    solenoid_time_s: float
    initial_weight_g: float
    final_weight_g: float
    reward_count: int
    reward_size_ul_per_drop: float


@dataclass(frozen=True)
class CalibrationEstimate:
    """Store the estimated solenoid time for a target reward size."""

    target_reward_size_ul: float
    suggested_solenoid_time_s: float | None
    lower_result: CalibrationResult | None
    upper_result: CalibrationResult | None
    method: str
    message: str
    warning: str | None = None

    @property
    def is_available(self) -> bool:
        """Return True when a target solenoid time could be estimated."""

        return self.suggested_solenoid_time_s is not None


class GpiozeroPulsePump:
    """Deliver GPIO19 rewards using the same six-pulse pattern as the task."""

    def __init__(self, pin: int = DEFAULT_PUMP_PIN) -> None:
        from gpiozero import LED

        self._led = LED(pin)

    def reward(
        self,
        which_pump: str,
        on_time_s: float,
        off_time_s: float,
        pulse_count: int,
    ) -> None:
        """Deliver one reward as a blocking pulse train."""

        if which_pump != "1":
            raise ValueError("calibration.py only supports pump '1' on GPIO19")
        self._led.blink(on_time_s, off_time_s, pulse_count, background=False)

    def off(self) -> None:
        """Turn the solenoid output off."""

        self._led.off()

    def close(self) -> None:
        """Release the GPIO output pin."""

        self._led.close()


def format_solenoid_times(solenoid_times_s: Sequence[float]) -> str:
    """Format solenoid times for terminal display."""

    return ", ".join(f"{value:.4f}".rstrip("0").rstrip(".") for value in solenoid_times_s)


def read_yes_no(prompt: str, default: bool = True) -> bool:
    """Read a yes/no response, accepting Enter as the selected default."""

    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        response = input(prompt + suffix).strip().lower()
        if not response:
            return default
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Please enter y or n.")


def read_decimal(prompt: str, *, allow_blank: bool = False) -> Decimal | None:
    """Read a decimal value from the terminal with validation."""

    while True:
        raw_value = input(prompt).strip()
        if allow_blank and not raw_value:
            return None
        try:
            value = Decimal(raw_value)
        except InvalidOperation:
            print("Please enter a number, for example 0.075.")
            continue
        if not value.is_finite():
            print("Please enter a finite number.")
            continue
        return value


def generate_solenoid_times(
    start_time_s: Decimal | float | str,
    end_time_s: Decimal | float | str,
    step_size_s: Decimal | float | str | None = None,
    measurement_count: int = DEFAULT_MANUAL_MEASUREMENT_COUNT,
) -> tuple[list[float], float, bool]:
    """
    Generate an inclusive list of solenoid times.

    When ``step_size_s`` is omitted, evenly spaced values are generated so the
    list contains ``measurement_count`` measurements, including both endpoints.

    Returns
    -------
    solenoid_times_s
        Inclusive test times as floats.
    actual_step_size_s
        The requested step, or the automatically calculated regular step.
    final_interval_shortened
        True when a manual step does not land exactly on the ending value and a
        shorter final interval was appended to include the requested endpoint.
    """

    start = Decimal(str(start_time_s))
    end = Decimal(str(end_time_s))

    if start <= 0:
        raise ValueError("The starting solenoid time must be greater than zero.")
    if end <= start:
        raise ValueError("The ending solenoid time must be greater than the starting time.")
    if measurement_count < 2:
        raise ValueError("measurement_count must be at least 2.")

    if step_size_s is None:
        step = (end - start) / Decimal(measurement_count - 1)
        values = [start + step * index for index in range(measurement_count)]
        values[-1] = end
        return [float(value) for value in values], float(step), False

    step = Decimal(str(step_size_s))
    if step <= 0:
        raise ValueError("The step size must be greater than zero.")
    if step > end - start:
        raise ValueError("The step size cannot be larger than the selected range.")

    values = [start]
    next_value = start + step
    while next_value < end:
        values.append(next_value)
        next_value += step

    final_interval_shortened = next_value != end
    values.append(end)

    return [float(value) for value in values], float(step), final_interval_shortened


def choose_solenoid_times_interactively(
    default_times_s: Sequence[float] = DEFAULT_SOLENOID_TIMES_S,
) -> list[float]:
    """Let the user select the default times or construct a manual range."""

    print("\nDefault solenoid times (seconds):")
    print(f"  {format_solenoid_times(default_times_s)}")

    if read_yes_no("Use the default solenoid times?", default=True):
        return list(default_times_s)

    while True:
        print("\nEnter a manual solenoid-time range.")
        start = read_decimal("Starting/smaller time in seconds: ")
        end = read_decimal("Ending/larger time in seconds: ")
        step = read_decimal(
            "Step size in seconds [press Enter for 5 evenly spaced measurements]: ",
            allow_blank=True,
        )

        try:
            times, actual_step, shortened = generate_solenoid_times(
                start_time_s=start,
                end_time_s=end,
                step_size_s=step,
            )
        except ValueError as error:
            print(f"Invalid range: {error}")
            continue

        if step is None:
            print(
                f"No step was entered. Using {actual_step:.6g} s to create "
                f"{len(times)} measurements."
            )
        elif shortened:
            final_interval = times[-1] - times[-2]
            print(
                "Note: the requested step does not land exactly on the ending "
                f"value, so the final interval is {final_interval:.6g} s."
            )

        print("\nThe following solenoid times will be tested:")
        print(f"  {format_solenoid_times(times)}")
        if read_yes_no("Continue with these values?", default=True):
            return times


def calculate_reward_size_ul_per_drop(
    initial_weight_g: float,
    final_weight_g: float,
    reward_count: int,
) -> float:
    """Convert collected water weight into mean reward size."""

    if reward_count <= 0:
        raise ValueError("reward_count must be greater than zero")
    if final_weight_g < initial_weight_g:
        raise ValueError(
            "final_weight_g must be greater than or equal to initial_weight_g"
        )

    collected_water_g = final_weight_g - initial_weight_g
    collected_water_ul = collected_water_g * 1000.0
    return collected_water_ul / reward_count


def deliver_rewards(
    pump,
    solenoid_time_s: float,
    reward_count: int = DEFAULT_REWARD_COUNT,
    off_time_s: float = DEFAULT_OFF_TIME_S,
    pulse_count: int = DEFAULT_PULSE_COUNT,
    inter_reward_interval_s: float = DEFAULT_INTER_REWARD_INTERVAL_S,
    sleep_fn=sleep,
) -> None:
    """Deliver repeated rewards for one solenoid timing condition."""

    for reward_index in range(reward_count):
        print(f"reward {reward_index + 1}/{reward_count}")
        pump.reward("1", solenoid_time_s, off_time_s, pulse_count)
        if inter_reward_interval_s > 0:
            sleep_fn(inter_reward_interval_s)


def read_float(prompt: str) -> float:
    """Read a floating-point number from the terminal."""

    while True:
        raw_value = input(prompt)
        try:
            return float(raw_value)
        except ValueError:
            print("Please enter a number, for example 2.345")


def run_calibration(
    pump,
    solenoid_times_s: Sequence[float] = DEFAULT_SOLENOID_TIMES_S,
    reward_count: int = DEFAULT_REWARD_COUNT,
    off_time_s: float = DEFAULT_OFF_TIME_S,
    pulse_count: int = DEFAULT_PULSE_COUNT,
    inter_reward_interval_s: float = DEFAULT_INTER_REWARD_INTERVAL_S,
) -> list[CalibrationResult]:
    """Run the full interactive calibration sequence."""

    results: list[CalibrationResult] = []
    for solenoid_time_s in solenoid_times_s:
        print("\n" + "=" * 60)
        print(f"Solenoid time: {solenoid_time_s:.4f} s")
        initial_weight_g = read_float(
            "Enter starting tube/container weight in grams: "
        )
        input(
            f"Press Enter to deliver {reward_count} rewards at "
            f"{solenoid_time_s:.4f} s."
        )
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


def estimate_solenoid_time_for_target(
    results: Sequence[CalibrationResult],
    target_reward_size_ul: float = DEFAULT_TARGET_REWARD_SIZE_UL,
) -> CalibrationEstimate:
    """Estimate a target solenoid time using adjacent-point interpolation."""

    if not results:
        return CalibrationEstimate(
            target_reward_size_ul=target_reward_size_ul,
            suggested_solenoid_time_s=None,
            lower_result=None,
            upper_result=None,
            method="unavailable",
            message="No calibration measurements were provided.",
        )

    sorted_results = sorted(results, key=lambda result: result.solenoid_time_s)
    tolerance = 1e-12

    for result in sorted_results:
        if abs(result.reward_size_ul_per_drop - target_reward_size_ul) <= tolerance:
            return CalibrationEstimate(
                target_reward_size_ul=target_reward_size_ul,
                suggested_solenoid_time_s=result.solenoid_time_s,
                lower_result=result,
                upper_result=result,
                method="exact measured value",
                message=(
                    f"A measured point already equals {target_reward_size_ul:.3f} "
                    "uL/drop."
                ),
            )

    candidate_pairs: list[tuple[CalibrationResult, CalibrationResult]] = []
    for first, second in zip(sorted_results, sorted_results[1:]):
        first_offset = first.reward_size_ul_per_drop - target_reward_size_ul
        second_offset = second.reward_size_ul_per_drop - target_reward_size_ul
        if first_offset * second_offset < 0:
            candidate_pairs.append((first, second))

    if not candidate_pairs:
        reward_sizes = [result.reward_size_ul_per_drop for result in sorted_results]
        minimum_size = min(reward_sizes)
        maximum_size = max(reward_sizes)
        if maximum_size < target_reward_size_ul:
            recommendation = "Repeat calibration using larger solenoid times."
        elif minimum_size > target_reward_size_ul:
            recommendation = "Repeat calibration using smaller solenoid times."
        else:
            recommendation = (
                "The data do not provide a valid adjacent bracket; inspect the "
                "measurements and repeat noisy conditions."
            )

        return CalibrationEstimate(
            target_reward_size_ul=target_reward_size_ul,
            suggested_solenoid_time_s=None,
            lower_result=None,
            upper_result=None,
            method="unavailable without extrapolation",
            message=(
                f"Target {target_reward_size_ul:.3f} uL/drop is not bracketed by "
                f"adjacent measurements. Measured range: {minimum_size:.3f}-"
                f"{maximum_size:.3f} uL/drop. {recommendation}"
            ),
        )

    # Prefer the pair that brackets the target most tightly in reward-size space.
    first, second = min(
        candidate_pairs,
        key=lambda pair: (
            abs(pair[0].reward_size_ul_per_drop - target_reward_size_ul)
            + abs(pair[1].reward_size_ul_per_drop - target_reward_size_ul),
            abs(pair[1].solenoid_time_s - pair[0].solenoid_time_s),
        ),
    )

    x1 = first.solenoid_time_s
    x2 = second.solenoid_time_s
    y1 = first.reward_size_ul_per_drop
    y2 = second.reward_size_ul_per_drop

    if abs(y2 - y1) <= tolerance:
        return CalibrationEstimate(
            target_reward_size_ul=target_reward_size_ul,
            suggested_solenoid_time_s=None,
            lower_result=first,
            upper_result=second,
            method="unavailable",
            message="The bracketing measurements have identical reward sizes.",
        )

    suggested_time = x1 + (target_reward_size_ul - y1) * (x2 - x1) / (y2 - y1)
    warning = None
    if len(candidate_pairs) > 1:
        warning = (
            "Multiple adjacent pairs cross the target, suggesting a non-monotonic "
            "or noisy calibration curve. The tightest bracket was used."
        )

    return CalibrationEstimate(
        target_reward_size_ul=target_reward_size_ul,
        suggested_solenoid_time_s=suggested_time,
        lower_result=first,
        upper_result=second,
        method="linear interpolation between adjacent measurements",
        message=(
            f"Estimated {target_reward_size_ul:.3f} uL/drop at "
            f"{suggested_time:.6f} s."
        ),
        warning=warning,
    )


def write_results_csv(
    results: Sequence[CalibrationResult], output_path: str | Path
) -> Path:
    """Save raw calibration measurements to a CSV file."""

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


def write_recommendation_csv(
    estimate: CalibrationEstimate, output_path: str | Path
) -> Path:
    """Save the target estimate and interpolation metadata to a CSV file."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lower = estimate.lower_result
    upper = estimate.upper_result
    fieldnames = [
        "target_reward_size_ul",
        "suggested_solenoid_time_s",
        "method",
        "lower_solenoid_time_s",
        "lower_reward_size_ul_per_drop",
        "upper_solenoid_time_s",
        "upper_reward_size_ul_per_drop",
        "message",
        "warning",
    ]
    with output_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "target_reward_size_ul": estimate.target_reward_size_ul,
                "suggested_solenoid_time_s": estimate.suggested_solenoid_time_s,
                "method": estimate.method,
                "lower_solenoid_time_s": None if lower is None else lower.solenoid_time_s,
                "lower_reward_size_ul_per_drop": (
                    None if lower is None else lower.reward_size_ul_per_drop
                ),
                "upper_solenoid_time_s": None if upper is None else upper.solenoid_time_s,
                "upper_reward_size_ul_per_drop": (
                    None if upper is None else upper.reward_size_ul_per_drop
                ),
                "message": estimate.message,
                "warning": estimate.warning,
            }
        )
    return output_path


def plot_calibration_curve(
    results: Sequence[CalibrationResult],
    output_path: str | Path,
    estimate: CalibrationEstimate | None = None,
) -> Path:
    """Plot measurements and visually mark the target reward estimate."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(
        "MPLCONFIGDIR", str(output_path.parent / ".matplotlib_cache")
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sorted_results = sorted(results, key=lambda result: result.solenoid_time_s)
    solenoid_times_s = [result.solenoid_time_s for result in sorted_results]
    reward_sizes_ul = [result.reward_size_ul_per_drop for result in sorted_results]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(
        solenoid_times_s,
        reward_sizes_ul,
        marker="o",
        linewidth=1.8,
        color="black",
        label="Measured calibration",
    )

    if estimate is not None:
        target = estimate.target_reward_size_ul
        ax.axhline(
            target,
            linestyle="--",
            linewidth=1.5,
            color="tab:blue",
            label=f"Target: {target:.3f} uL/drop",
        )

        if estimate.is_available:
            suggested_time = estimate.suggested_solenoid_time_s
            assert suggested_time is not None

            ax.axvline(
                suggested_time,
                linestyle="--",
                linewidth=1.5,
                color="tab:red",
                label=f"Estimated time: {suggested_time:.4f} s",
            )
            ax.scatter(
                [suggested_time],
                [target],
                s=100,
                marker="*",
                color="tab:red",
                edgecolor="black",
                linewidth=0.7,
                zorder=6,
                label="Estimated 3 uL point",
            )

            lower = estimate.lower_result
            upper = estimate.upper_result
            if lower is not None and upper is not None and lower is not upper:
                bracket_x = [lower.solenoid_time_s, upper.solenoid_time_s]
                bracket_y = [
                    lower.reward_size_ul_per_drop,
                    upper.reward_size_ul_per_drop,
                ]
                ax.scatter(
                    bracket_x,
                    bracket_y,
                    s=110,
                    facecolors="none",
                    edgecolors="tab:orange",
                    linewidths=2,
                    zorder=5,
                    label="Points used for interpolation",
                )

            ax.annotate(
                f"Target = {target:.3f} uL/drop\n"
                f"Estimated time = {suggested_time:.4f} s",
                xy=(suggested_time, target),
                xytext=(12, 18),
                textcoords="offset points",
                arrowprops={"arrowstyle": "->", "color": "tab:red"},
                bbox={
                    "boxstyle": "round,pad=0.35",
                    "facecolor": "white",
                    "edgecolor": "tab:red",
                    "alpha": 0.9,
                },
            )
        else:
            ax.text(
                0.02,
                0.98,
                "3 uL target is outside the usable measured bracket.\n"
                "Repeat calibration with an expanded time range.",
                transform=ax.transAxes,
                va="top",
                ha="left",
                bbox={
                    "boxstyle": "round,pad=0.35",
                    "facecolor": "white",
                    "edgecolor": "tab:red",
                    "alpha": 0.9,
                },
            )

    ax.set_xlabel("Solenoid time (s)")
    ax.set_ylabel("Reward size (uL/drop)")
    ax.set_title("Reward calibration with 3 uL target estimate")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def print_estimate_summary(estimate: CalibrationEstimate) -> None:
    """Print a user-friendly interpolation summary."""

    print("\n" + "-" * 60)
    print(f"Target reward size: {estimate.target_reward_size_ul:.3f} uL/drop")

    if estimate.is_available:
        lower = estimate.lower_result
        upper = estimate.upper_result
        if lower is not None and upper is not None and lower is not upper:
            print("Measurements used for interpolation:")
            print(
                f"  {lower.solenoid_time_s:.4f} s -> "
                f"{lower.reward_size_ul_per_drop:.3f} uL/drop"
            )
            print(
                f"  {upper.solenoid_time_s:.4f} s -> "
                f"{upper.reward_size_ul_per_drop:.3f} uL/drop"
            )
        print(
            "Recommended solenoid time: "
            f"{estimate.suggested_solenoid_time_s:.6f} s"
        )
        print(f"Method: {estimate.method}")
    else:
        print("No safe interpolation estimate is available.")
        print(estimate.message)

    if estimate.warning:
        print(f"Warning: {estimate.warning}")


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

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
    parser.add_argument(
        "--target-ul",
        type=float,
        default=DEFAULT_TARGET_REWARD_SIZE_UL,
        help="Target reward size in uL/drop. Default: 3.0.",
    )
    return parser


def main() -> None:
    """Run standalone calibration from the command line."""

    parser = build_argument_parser()
    args = parser.parse_args()

    if args.reward_count <= 0:
        parser.error("--reward-count must be greater than zero")
    if args.inter_reward_interval < 0:
        parser.error("--inter-reward-interval cannot be negative")
    if args.target_ul <= 0:
        parser.error("--target-ul must be greater than zero")

    solenoid_times_s = choose_solenoid_times_interactively()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.output_dir / f"reward_calibration_{timestamp}.csv"
    recommendation_path = (
        args.output_dir / f"reward_calibration_recommendation_{timestamp}.csv"
    )
    plot_path = args.output_dir / f"reward_calibration_{timestamp}.png"

    pump = GpiozeroPulsePump()
    try:
        results = run_calibration(
            pump=pump,
            solenoid_times_s=solenoid_times_s,
            reward_count=args.reward_count,
            inter_reward_interval_s=args.inter_reward_interval,
        )
    except KeyboardInterrupt:
        print("\nCalibration stopped by user.")
        return
    finally:
        pump.off()
        pump.close()

    estimate = estimate_solenoid_time_for_target(
        results,
        target_reward_size_ul=args.target_ul,
    )
    written_csv_path = write_results_csv(results, csv_path)
    written_recommendation_path = write_recommendation_csv(
        estimate, recommendation_path
    )
    written_plot_path = plot_calibration_curve(
        results,
        plot_path,
        estimate=estimate,
    )

    print_estimate_summary(estimate)
    print("\nCalibration complete.")
    print(f"Saved measurements CSV: {written_csv_path}")
    print(f"Saved recommendation CSV: {written_recommendation_path}")
    print(f"Saved annotated plot: {written_plot_path}")


if __name__ == "__main__":
    main()
