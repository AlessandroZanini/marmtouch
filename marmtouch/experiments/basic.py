import time

from marmtouch.experiments.base import Experiment
from marmtouch.experiments.trialrecord import TrialRecord


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

        start_time = current_time = time.time()
        info = {"touch": 0, "RT": 0}
        while (current_time - start_time) < timing["target_duration"]:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if self.was_tapped(
                    stimuli["target"]["loc"], tap, stimuli["target"]["window"]
                ):
                    info = {
                        "touch": 1 if info["touch"] == 0 else 3,
                        "RT": current_time - start_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    if timing["correct_duration"]:
                        self.screen.fill(self.background)
                        if stimuli['correct'] is not None:
                            self.draw_stimulus(**stimuli["correct"])
                        self.flip()
                        self.good_monkey()
                        start_time = time.time()
                        while (time.time() - start_time) < timing["correct_duration"]:
                            self.parse_events()
                            if not self.running:
                                return
                    else:
                        self.good_monkey()
                    self.screen.fill(self.background)
                    self.flip()
                    break
                else:
                    for distractor in distractors:
                        if self.was_tapped(
                            distractor["loc"], tap, distractor["window"],
                        ):
                            break
                    else:
                        if self.options.get("ignore_outside", False):
                            continue
                    info = {
                        "touch": 2,
                        "RT": current_time - start_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    if self.options.get("ignore_incorrect", False):
                        continue
                    elif self.options.get("reward_incorrect", False):
                        self.good_monkey()
                    elif timing["incorrect_duration"]:
                        self.screen.fill(self.background)
                        if stimuli['incorrect'] is not None:
                            self.draw_stimulus(**stimuli["incorrect"])
                        self.flip()
                        start_time = time.time()
                        while (time.time() - start_time) < timing["incorrect_duration"]:
                            self.parse_events()
                            if not self.running:
                                return
                    self.screen.fill(self.background)
                    self.flip()
                    break
        if not self.running:
            return
        return info

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
        self.start_time = time.time()

        while self.running:
            self.update_info(trial)
            self._run_intertrial_interval(3)
            if not self.running:
                return

            # TODO: extract initialize trial parameters into a method and add stimuli/timing to self.trial
            condition = self.get_condition()
            if condition is None:
                break

            condition_items = self.conditions[condition]
            stimuli = {
                stimulus: self.get_item(condition_items.get(stimulus)) if stimulus in condition_items else None
                for stimulus in ["target", "correct", "incorrect"]
            }
            if stimuli['target'] is None:
                raise ValueError(f"Target stimulus not defined for condition {condition}")

            distractors = condition_items.get("distractors")
            if distractors is not None:
                stimuli["distractors"] = [
                    self.get_item(distractor) for distractor in distractors
                ]

            timing = {
                f"{event}_duration": self.get_duration(event)
                for event in ["target", "correct", "incorrect"]
            }

            if self.options.get("push_to_start", False):
                start_result = self._start_trial()
                if start_result is None:
                    continue
                if not self.running:
                    return
            self.TTLout["sync"].pulse(0.1)
            if self.camera is not None:
                self.camera.start_recording(
                    (self.data_dir / f"{trial}.h264").as_posix()
                )

            # initialize trial parameters
            trial_start_time = time.time() - self.start_time
            self.trial = TrialRecord(
                self.keys,
                trial=trial,
                trial_start_time=trial_start_time,
                condition=condition,
                target_touch=0,
                target_RT=0,
                **timing,
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
