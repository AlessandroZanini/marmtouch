from marmtouch.experiments.base import Experiment

from collections import Counter
import random
import time


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

    def _show_target(self, stimuli, timing):
        self.screen.fill(self.background)
        self.draw_stimulus(**stimuli["target"])

        distractors = stimuli.get("distractors")
        if distractors is not None:
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
                        self.draw_stimulus(**stimuli["correct"])
                        self.flip()
                        self.good_monkey()
                        start_time = time.time()
                        while (time.time() - start_time) < timing["correct_duration"]:
                            self.parse_events()
                    else:
                        self.good_monkey()
                    self.screen.fill(self.background)
                    self.flip()
                    break
                else:
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
                        self.draw_stimulus(**stimuli["incorrect"])
                        self.flip()
                        start_time = time.time()
                        while (time.time() - start_time) < timing["incorrect_duration"]:
                            self.parse_events()
                    self.screen.fill(self.background)
                    self.flip()
                    break
        return info

    def run(self):
        if self.options.get("reward_incorrect", False) and self.options.get(
            "ignore_incorrect", False
        ):
            raise ValueError(
                "ignore_incorrect and reward_incorrect cannot both be true"
            )
        self.initialize()
        self.info = {condition: Counter() for condition in self.conditions.keys()}

        trial = 0
        self.running = True
        self.start_time = time.time()

        while self.running:
            self.update_info(trial)

            # iti
            start_time = time.time()
            while time.time() - start_time < self.options.get("iti", 3):
                self.parse_events()
                if not self.running:
                    return

            # initialize trial parameters
            if self.blocks is None:
                condition = random.choice(list(self.conditions.keys()))
            else:
                condition = self.get_condition()
            stimuli = {
                stimulus: self.get_item(self.conditions[condition][stimulus])
                for stimulus in ["target", "correct", "incorrect"]
            }

            distractors = self.conditions[condition].get("distractors")
            if distractors is not None:
                stimuli["distractors"] = [
                    self.get_item(distractor) for distractor in distractors
                ]

            timing = {
                f"{event}_duration": self.get_duration(event)
                for event in ["target", "correct", "incorrect"]
            }
            trial_start_time = time.time() - self.start_time
            trialdata = dict(
                trial=trial,
                trial_start_time=trial_start_time,
                condition=condition,
                target_touch=0,
                target_RT=0,
                **timing,
            )

            if self.options.get("push_to_start", False):
                start_result = self._start_trial()
                if start_result is None:
                    continue
            self.TTLout["sync"].pulse(0.1)
            if self.camera is not None:
                self.camera.start_recording(
                    (self.data_dir / f"{trial}.h264").as_posix()
                )

            # run trial
            target_result = self._show_target(stimuli, timing)
            if target_result is None:
                return

            trialdata.update(
                {
                    "target_touch": target_result.get("touch", 0),
                    "target_RT": target_result.get("RT", 0),
                }
            )

            # wipe screen
            self.screen.fill(self.background)
            self.flip()

            if self.camera is not None:
                self.camera.stop_recording()
            self.dump_trialdata(trialdata)
            trial += 1
            self.info[condition][trialdata["target_touch"]] += 1
            if self.blocks is not None:
                self.update_condition_list(correct=(trialdata["target_touch"] == 1))
