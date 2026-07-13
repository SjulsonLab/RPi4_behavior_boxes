"""
Tests for the standalone solenoid calibration script.

The tests use fake pump/input objects so no Raspberry Pi GPIO pins are touched.
"""

import csv

import calibration


class FakePump:
    """Record reward calls without touching hardware."""

    def __init__(self):
        self.calls = []

    def reward(self, which_pump, on_time_s, off_time_s, pulse_count):
        """
        Record one requested reward.

        Parameters
        ----------
        which_pump : str
            Pump identifier; "1" means GPIO19 in the behavior box code.
        on_time_s : float
            Solenoid open time for each pulse, in seconds.
        off_time_s : float
            Time between pulses, in seconds.
        pulse_count : int
            Number of pulses used for one reward.

        Returns
        -------
        None
            The call is appended to ``self.calls``.
        """
        self.calls.append((which_pump, on_time_s, off_time_s, pulse_count))


def test_default_solenoid_times_are_point_one_to_one_second():
    assert calibration.DEFAULT_SOLENOID_TIMES_S == [
        0.1,
        0.2,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1.0,
    ]


def test_calculate_reward_size_converts_grams_to_microliters_per_drop():
    reward_size_ul = calibration.calculate_reward_size_ul_per_drop(
        initial_weight_g=2.000,
        final_weight_g=2.250,
        reward_count=100,
    )

    assert reward_size_ul == 2.5


def test_deliver_rewards_uses_current_six_pulse_reward_style():
    fake_pump = FakePump()

    calibration.deliver_rewards(
        pump=fake_pump,
        solenoid_time_s=0.3,
        reward_count=3,
        off_time_s=0.01,
        pulse_count=6,
        inter_reward_interval_s=0,
        sleep_fn=lambda seconds: None,
    )

    assert fake_pump.calls == [
        ("1", 0.3, 0.01, 6),
        ("1", 0.3, 0.01, 6),
        ("1", 0.3, 0.01, 6),
    ]


def test_write_results_csv_uses_solenoid_time_and_reward_size_columns(tmp_path):
    results = [
        calibration.CalibrationResult(
            solenoid_time_s=0.1,
            initial_weight_g=1.0,
            final_weight_g=1.2,
            reward_count=100,
            reward_size_ul_per_drop=2.0,
        ),
        calibration.CalibrationResult(
            solenoid_time_s=0.2,
            initial_weight_g=1.0,
            final_weight_g=1.3,
            reward_count=100,
            reward_size_ul_per_drop=3.0,
        ),
    ]
    output_path = tmp_path / "calibration.csv"

    calibration.write_results_csv(results, output_path)

    with output_path.open(newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows == [
        {
            "solenoid_time_s": "0.1",
            "initial_weight_g": "1.0",
            "final_weight_g": "1.2",
            "reward_count": "100",
            "reward_size_ul_per_drop": "2.0",
        },
        {
            "solenoid_time_s": "0.2",
            "initial_weight_g": "1.0",
            "final_weight_g": "1.3",
            "reward_count": "100",
            "reward_size_ul_per_drop": "3.0",
        },
    ]


def test_plot_calibration_curve_writes_png_file(tmp_path):
    results = [
        calibration.CalibrationResult(
            solenoid_time_s=0.1,
            initial_weight_g=1.0,
            final_weight_g=1.2,
            reward_count=100,
            reward_size_ul_per_drop=2.0,
        ),
        calibration.CalibrationResult(
            solenoid_time_s=0.2,
            initial_weight_g=1.0,
            final_weight_g=1.3,
            reward_count=100,
            reward_size_ul_per_drop=3.0,
        ),
    ]
    output_path = tmp_path / "calibration_curve.png"

    calibration.plot_calibration_curve(results, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
