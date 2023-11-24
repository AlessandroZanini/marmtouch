import time

from marmtouch.experiments.base import Experiment
from marmtouch.experiments.trialrecord import TrialRecord
from marmtouch.experiments.util.events import get_first_tap, was_tapped


class Basic(Experiment):
    keys = (
        "trial",
        "trial_start_time",
        "condition",
        "target_touch",
        "target_RT",
        "target_duration",
        "correct_duration",
        "incorrect_duration",
        "sync_onset",
        "start_stimulus_onset",
        "start_stimulus_offset",
    )
    name = "Basic"
    info_background = (0, 0, 0)
    info_breakdown_keys = {
        "Condition": "condition",
    }
    outcome_key = "target_touch"

    def _show_target(self, stimuli, timing):
        self.screen.fill(self.background)
        self.draw_stimulus(**stimuli["target"])

        distractors = stimuli.get("distractors", [])
        for distractor in distractors:
            self.draw_stimulus(**distractor)
        self.flip()

        info = {"touch": 0, "RT": 0}
        self.clock.wait(timing["target_duration"])
        while self.clock.waiting():
            tap = get_first_tap(self.event_manager.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if was_tapped(
                    stimuli["target"]["loc"], tap, stimuli["target"]["window"]
                ):
                    info = {
                        "touch": 1 if info["touch"] == 0 else 3,
                        "RT": self.clock.elapsed_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    if timing["correct_duration"]:
                        self.screen.fill(self.background)
                        if stimuli["correct"] is not None:
                            self.draw_stimulus(**stimuli["correct"])
                        self.flip()
                        self.good_monkey()
                        self.clock.wait(timing["correct_duration"])
                        while self.clock.waiting():
                            self.event_manager.parse_events()
                            if not self.running:
                                return
                    else:
                        self.good_monkey()
                    self.screen.fill(self.background)
                    self.flip()
                    break
                else:
                    for distractor in distractors:
                        if was_tapped(
                            distractor["loc"],
                            tap,
                            distractor["window"],
                        ):
                            break
                    else:
                        if self.options.get("ignore_outside", False):
                            continue
                    info = {
                        "touch": 2,
                        "RT": self.clock.elapsed_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    if self.options.get("ignore_incorrect", False):
                        continue
                    elif self.options.get("reward_incorrect", False):
                        self.good_monkey()
                    elif timing["incorrect_duration"]:
                        self.screen.fill(self.background)
                        if stimuli["incorrect"] is not None:
                            self.draw_stimulus(**stimuli["incorrect"])
                        self.flip()
                        self.clock.wait(timing["incorrect_duration"])
                        while self.clock.waiting():
                            self.event_manager.parse_events()
                            if not self.running:
                                return
                    self.screen.fill(self.background)
                    self.flip()
                    break
        if not self.running:
            return
        return info

    def get_stimuli(self, condition):
        condition_items = self.conditions[condition]
        stimuli = {
            stimulus: self.get_item(condition_items.get(stimulus))
            if stimulus in condition_items
            else None
            for stimulus in ["target", "correct", "incorrect"]
        }
        if stimuli["target"] is None:
            raise ValueError(
                f"Target stimulus not defined for condition {condition}"
            )

        distractors = condition_items.get("distractors")
        if distractors is not None:
            stimuli["distractors"] = [
                self.get_item(distractor) for distractor in distractors
            ]
        return stimuli

    def get_timing(self, condition):
        timing = {
            f"{event}_duration": self.get_duration(event)
            for event in ["target", "correct", "incorrect"]
        }
        return timing

    def run(self):
        if self.options.get("reward_incorrect", False) and self.options.get(
            "ignore_incorrect", False
        ):
            raise ValueError(
                "ignore_incorrect and reward_incorrect cannot both be true"
            )
        self.initialize()
        trial = 0
        self.running = True
        while self.running:
            self.update_info(trial)
            self._run_intertrial_interval(3)
            if not self.running:
                return

            # TODO: extract initialize trial parameters into a method and add stimuli/timing to self.trial
            condition = self.get_condition()
            if condition is None:
                break

            stimuli = self.get_stimuli(condition)
            timing = self.get_timing(condition)

            if self.options.get("push_to_start", False):
                start_result = self._start_trial()
                if start_result is None:
                    continue
                if not self.running:
                    return
            SYNC_PULSE_DURATION = 0.1
            self.TTLout["sync"].pulse(SYNC_PULSE_DURATION)
            if self.camera is not None:
                self.camera.start_recording(
                    (self.data_dir / f"{trial}.h264").as_posix()
                )

            # initialize trial parameters
            trial_start_time = self.clock.get_time()
            self.trial = TrialRecord(
                self.keys,
                trial=trial,
                trial_start_time=trial_start_time,
                condition=condition,
                target_touch=0,
                target_RT=0,
                sync_onset=-SYNC_PULSE_DURATION,
                **timing,
            )
            if self.options.get("push_to_start", False):
                start_stimulus_offset = -(
                    SYNC_PULSE_DURATION + start_result["start_stimulus_delay"]
                )
                self.trial.data.update(
                    dict(
                        start_stimulus_offset=start_stimulus_offset,
                        start_stimulus_onset=start_stimulus_offset - start_result["RT"],
                    )
                )

            # run trial
            target_result = self._show_target(stimuli, timing)
            if target_result is None:
                return

            self.trial.data.update(
                {
                    "target_touch": target_result.get("touch", 0),
                    "target_RT": target_result.get("RT", 0),
                }
            )
            outcome = self.trial.data["target_touch"]

            # wipe screen
            self.screen.fill(self.background)
            self.flip()

            # end of trial cleanup
            if self.camera is not None:
                self.camera.stop_recording()
            self.dump_trialdata()
            if self.reached_max_responses():
                break
            trial += 1
            self.update_condition_list(outcome)


    def _test_trial(self, test):
        self._setup_test_trial(test)
        self.update_info(test['trial'])
        stimuli = self.get_stimuli(test['condition'])
        timing = self.get_timing(test['condition'])

        # run trial
        target_result = self._show_target(stimuli, timing)
        if target_result is None:
            return
        # wipe screen
        self.screen.fill(self.background)
        self.flip()
