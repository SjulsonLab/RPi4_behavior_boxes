"""
Tests for the standalone solenoid calibration script.

The tests use fake pump/input objects so no Raspberry Pi GPIO pins are touched.
"""

import csv

import calibration
import pytest


class FakePump:
    """Record reward calls without touching hardware."""

    def __init__(self):
        self.calls = []
        self.off_called = False
        self.close_called = False

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

    def off(self):
        self.off_called = True

    def close(self):
        self.close_called = True


def test_default_solenoid_times_match_production_values():
    assert calibration.DEFAULT_SOLENOID_TIMES_S == [
        0.05,
        0.075,
        0.1,
        0.125,
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


@pytest.mark.parametrize("response", ["", "y"])
def test_target_selection_uses_default_when_enter_or_yes(monkeypatch, response):
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or response)

    target = calibration.choose_target_reward_size()

    assert target == 3.0
    assert prompts == [
        "Target reward volume: 3.0 uL\nUse the default target volume? [Y/n]: "
    ]


def test_target_selection_accepts_custom_volume(monkeypatch):
    responses = iter(["n", "5"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(responses))

    assert calibration.choose_target_reward_size() == 5.0


def test_target_selection_reprompts_for_invalid_custom_volumes(monkeypatch):
    responses = iter(["n", "0", "-2", "NaN", "Infinity", "bad", "5"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(responses))

    assert calibration.choose_target_reward_size() == 5.0


def test_explicit_target_does_not_prompt(monkeypatch):
    monkeypatch.setattr(
        "builtins.input", lambda _prompt: pytest.fail("unexpected target prompt")
    )

    assert calibration.choose_target_reward_size(4.0) == 4.0


@pytest.mark.parametrize("target", ["nan", "inf", "0", "-1"])
def test_invalid_cli_target_is_rejected_before_gpio_initialization(
    monkeypatch, target
):
    gpio_initialized = False

    def make_pump():
        nonlocal gpio_initialized
        gpio_initialized = True
        return FakePump()

    monkeypatch.setattr("sys.argv", ["calibration.py", "--target-ul", target])
    monkeypatch.setattr(calibration, "GpiozeroPulsePump", make_pump)

    with pytest.raises(SystemExit):
        calibration.main()

    assert not gpio_initialized


def _run_sweep(monkeypatch, measurements, target, *, early_stop=True, reward_count=1):
    weights = iter(
        weight
        for reward_size in measurements
        for weight in (0.0, reward_size * reward_count / 1000.0)
    )
    monkeypatch.setattr(calibration, "read_float", lambda _prompt: next(weights))
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    pump = FakePump()
    times = [0.05 + 0.025 * index for index in range(len(measurements))]
    results = calibration.run_calibration(
        pump,
        solenoid_times_s=times,
        reward_count=reward_count,
        inter_reward_interval_s=0,
        target_reward_size_ul=target,
        early_stop=early_stop,
    )
    return results, pump, times


def test_early_stops_after_first_bracket_and_interpolates_correctly(monkeypatch):
    results, pump, times = _run_sweep(
        monkeypatch, [2.0, 2.7, 3.4, 4.1], 3.0, reward_count=3
    )

    assert [result.reward_size_ul_per_drop for result in results] == pytest.approx(
        [2.0, 2.7, 3.4]
    )
    estimate = calibration.estimate_solenoid_time_for_target(results, 3.0)
    assert estimate.is_available
    assert estimate.suggested_solenoid_time_s == pytest.approx(
        times[1] + (3.0 - 2.7) * (times[2] - times[1]) / (3.4 - 2.7)
    )
    assert len(pump.calls) == len(results) * 3
    assert [call for call in pump.calls if call[1] == times[2]] == [
        ("1", times[2], calibration.DEFAULT_OFF_TIME_S, 6)
    ] * 3


def test_early_stops_at_exact_target_measurement(monkeypatch):
    results, _pump, _times = _run_sweep(monkeypatch, [2.0, 3.0, 4.0], 3.0)

    assert [result.reward_size_ul_per_drop for result in results] == [2.0, 3.0]
    estimate = calibration.estimate_solenoid_time_for_target(results, 3.0)
    assert estimate.method == "exact measured value"
    assert estimate.suggested_solenoid_time_s == results[1].solenoid_time_s


def test_custom_target_stops_after_its_first_bracket(monkeypatch):
    results, _pump, _times = _run_sweep(
        monkeypatch, [2.0, 3.4, 4.5, 5.5, 6.0], 5.0
    )

    assert [result.reward_size_ul_per_drop for result in results] == [
        2.0,
        3.4,
        4.5,
        5.5,
    ]
    assert calibration.estimate_solenoid_time_for_target(results, 5.0).is_available


def test_no_bracket_finishes_configured_range(monkeypatch):
    results, _pump, _times = _run_sweep(monkeypatch, [2.0, 3.4, 4.5], 5.0)

    assert len(results) == 3
    assert not calibration.estimate_solenoid_time_for_target(results, 5.0).is_available


def test_full_sweep_continues_after_bracket(monkeypatch):
    results, _pump, _times = _run_sweep(
        monkeypatch, [2.0, 2.7, 3.4, 4.1], 3.0, early_stop=False
    )

    assert len(results) == 4
    assert calibration.estimate_solenoid_time_for_target(results, 3.0).is_available


def test_cli_target_early_stop_writes_outputs_and_cleans_up_gpio(
    monkeypatch, tmp_path
):
    pump = FakePump()
    weights = iter([0.0, 0.004, 0.0, 0.006, 0.0, 0.009])
    times = [0.05, 0.075, 0.1, 0.125]

    def read_weight(_prompt):
        return next(weights)

    def confirm_delivery(prompt):
        assert prompt.startswith("Press Enter to deliver")
        return ""

    monkeypatch.setattr(
        "sys.argv",
        [
            "calibration.py",
            "--target-ul",
            "4",
            "--reward-count",
            "2",
            "--inter-reward-interval",
            "0",
            "--output-dir",
            str(tmp_path),
        ],
    )
    monkeypatch.setattr(calibration, "choose_solenoid_times_interactively", lambda: times)
    monkeypatch.setattr(calibration, "GpiozeroPulsePump", lambda: pump)
    monkeypatch.setattr(calibration, "read_float", read_weight)
    monkeypatch.setattr("builtins.input", confirm_delivery)

    calibration.main()

    measurement_files = [
        path
        for path in tmp_path.glob("reward_calibration_*.csv")
        if "recommendation" not in path.name
    ]
    recommendation_files = list(
        tmp_path.glob("reward_calibration_recommendation_*.csv")
    )
    plot_files = list(tmp_path.glob("reward_calibration_*.png"))
    assert len(measurement_files) == len(recommendation_files) == len(plot_files) == 1
    with measurement_files[0].open(newline="") as csv_file:
        measurements = list(csv.DictReader(csv_file))
    with recommendation_files[0].open(newline="") as csv_file:
        recommendation = next(csv.DictReader(csv_file))

    assert [row["reward_size_ul_per_drop"] for row in measurements] == [
        "2.0",
        "3.0",
        "4.5",
    ]
    assert recommendation["target_reward_size_ul"] == "4.0"
    assert float(recommendation["suggested_solenoid_time_s"]) == pytest.approx(
        0.075 + (4.0 - 3.0) * (0.1 - 0.075) / (4.5 - 3.0)
    )
    assert plot_files[0].stat().st_size > 0
    assert len(pump.calls) == 6
    assert pump.off_called
    assert pump.close_called


def test_full_sweep_cli_disables_early_stop(monkeypatch, tmp_path):
    pump = FakePump()
    weights = iter([0.0, 0.002, 0.0, 0.003, 0.0, 0.004])
    times = [0.05, 0.075, 0.1]

    monkeypatch.setattr(
        "sys.argv",
        [
            "calibration.py",
            "--target-ul",
            "3",
            "--full-sweep",
            "--reward-count",
            "1",
            "--inter-reward-interval",
            "0",
            "--output-dir",
            str(tmp_path),
        ],
    )
    monkeypatch.setattr(calibration, "choose_solenoid_times_interactively", lambda: times)
    monkeypatch.setattr(calibration, "GpiozeroPulsePump", lambda: pump)
    monkeypatch.setattr(calibration, "read_float", lambda _prompt: next(weights))
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    calibration.main()

    measurement_file = next(
        path
        for path in tmp_path.glob("reward_calibration_*.csv")
        if "recommendation" not in path.name
    )
    with measurement_file.open(newline="") as csv_file:
        measurements = list(csv.DictReader(csv_file))
    assert len(measurements) == len(times)
    assert len(pump.calls) == len(times)


def test_plot_labels_use_nondefault_target(tmp_path, monkeypatch):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    original_subplots = plt.subplots
    axes = []

    def capture_subplots(*args, **kwargs):
        figure, axis = original_subplots(*args, **kwargs)
        axes.append(axis)
        return figure, axis

    monkeypatch.setattr(plt, "subplots", capture_subplots)
    results = [
        calibration.CalibrationResult(0.05, 1.0, 1.003, 1, 3.0),
        calibration.CalibrationResult(0.075, 1.0, 1.005, 1, 5.0),
    ]
    estimate = calibration.estimate_solenoid_time_for_target(results, 4.0)

    calibration.plot_calibration_curve(results, tmp_path / "target_4.png", estimate)

    assert axes[0].get_title() == "Reward calibration with 4.000 uL target estimate"
    assert "Estimated 4.000 uL point" in axes[0].get_legend_handles_labels()[1]

    no_bracket = calibration.estimate_solenoid_time_for_target(results[:1], 5.0)
    calibration.plot_calibration_curve(
        results[:1], tmp_path / "target_5_no_bracket.png", no_bracket
    )
    assert "5.000 uL target is outside" in axes[1].texts[0].get_text()
