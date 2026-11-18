import unittest
from collections import Counter, defaultdict

from task_protocol.mmn_task.mmn_protocol import MMNConfig, build_schedule


class BuildScheduleTests(unittest.TestCase):
    def test_default_schedule_is_balanced_and_alternates_orientations(self) -> None:
        config = MMNConfig(random_seed=10)
        schedule = build_schedule(config)
        self.assertEqual(len(schedule), 6 * 96 * 8)

        by_block = defaultdict(list)
        for event in schedule:
            by_block[event.block_number].append(event)

        for block_number, events in by_block.items():
            by_trial = defaultdict(list)
            for event in events:
                by_trial[event.trial_number].append(event)

            counts = Counter(
                trial_events[0].standards_before_deviant
                for trial_events in by_trial.values()
            )
            self.assertEqual(counts, Counter({4: 24, 5: 24, 6: 24, 7: 24}))

            standard_orientation = 135 if block_number % 2 == 1 else 45
            deviant_orientation = 45 if block_number % 2 == 1 else 135
            for trial_events in by_trial.values():
                self.assertEqual(len(trial_events), config.stimuli_per_trial)
                deviants = [
                    event for event in trial_events
                    if event.stimulus_type == "deviant"
                ]
                self.assertEqual(len(deviants), 1)
                deviant = deviants[0]
                self.assertEqual(
                    deviant.sequence_position,
                    deviant.standards_before_deviant + 1,
                )
                self.assertEqual(deviant.orientation_deg, deviant_orientation)
                self.assertTrue(
                    all(
                        event.stimulus_type == "standard"
                        and event.orientation_deg == standard_orientation
                        for event in trial_events
                        if event is not deviant
                    )
                )

    def test_seed_reproduces_schedule(self) -> None:
        config = MMNConfig(
            block_count=1,
            trials_per_block=4,
            standard_count_options=(4,),
            random_seed=42,
        )
        self.assertEqual(build_schedule(config), build_schedule(config))

    def test_rejects_unbalanced_trial_count(self) -> None:
        with self.assertRaises(ValueError):
            MMNConfig(trials_per_block=95)


if __name__ == "__main__":
    unittest.main()
