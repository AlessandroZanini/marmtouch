import random
import time
from collections import Counter
from itertools import product

import pygame

from marmtouch.experiments.base import Experiment
from marmtouch.experiments.mixins.task_components.delay import DelayMixin
from marmtouch.experiments.trialrecord import TrialRecord


class Memory(Experiment, DelayMixin):
    """A delayed match to location task.
    
    This task is a delayed match to location task. The task is to tap the
    location of a cued stimulus location after a delay.

    Task Structure
    --------------
    CUE
        The :item:`cue` stimulus is presented for :time:`cue` seconds.
        
        If :opt:`cue_touch_enabled` is True, the subject must touch 
        cue within :time:`cue` seconds to proceed. Otherwise, touches 
        are logged and ignored.

    DELAY
        A blank screen is presented for :time:`delay` seconds, if :time:`delay` > 0.
        If :time:`delay` <= 0, this phase is skipped.
        
        If :item:`delay_distractor` is defined, a distractor stimulus is
        presented at :time:`delay_distractor_onset` seconds after delay 
        onset for :time:`delay_distractor_duration` seconds.
        Touches are logged and ignored.

    SAMPLE
        The :item:`target` and oally the :item:`distractors` are presented
        for :time:`sample` seconds.  If :time:`delay` < 0, :item:`cue` is also
        presented.

        If :opt:`ignore_outside` is True, touches outside of the :item:`target`
        and :item:`distractors` are ignored. Otherwise, touches outside of the 
        :item:`target` and :item:`distractors` are treated as incorrect.

        If :opt:`ignore_incorrect` is True, touches on :item:`distractors`
        are logged and ignored.  If a correct response is made after an
        incorrect response, the incorrect response is logged as outcome=3.

        If :opt:`reward_incorrect` is True, touches on :item:`distractors`
        are rewarded and trial is terminated.  No effect if 
        :opt:`ignore_incorrect` is True.

    Options
    -------
    cue_touch_enabled: bool, default False
        If True, the subject must touch the cue to proceed from cue phase.
    ignore_incorrect: bool, default False
        If True, incorrect responses during the sample phase are ignored.
        If the correct response is provided after the incorrect response, 
        it is logged as outcome 3.
    reward_incorrect: bool, default False
        If True, incorrect responses during the sample phase are rewarded.
    ignore_outside: bool, default False
        If True, touches outside of the target and distractors are ignored.
        Otherwise, touches outside of the target and distractors are treated 
        as incorrect.
    """
    keys = (
        "trial",
        "trial_start_time",
        "condition",
        "cue_touch",
        "cue_RT",
        "sample_touch",
        "sample_RT",
        "cue_duration",
        "delay_duration",
        "sample_duration",
        "correct_duration",
        "incorrect_duration",
        "delay_distractor_onset",
        "delay_distractor_duration",
        "tapped",
    )
    name = "Memory"
    info_background = (0, 0, 0)
    info_breakdown_keys = {
        "Condition": "condition",
        "Delay": "delay_duration",
    }
    outcome_key = "sample_touch"

    def _show_cue(self, stimuli, timing):
        self.screen.fill(self.background)
        self.draw_stimulus(**stimuli["cue"])
        self.flip()

        start_time = current_time = time.time()
        info = {"touch": 0, "RT": 0}
        while (current_time - start_time) < timing["cue_duration"]:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is not None:
                if self.was_tapped(
                    stimuli["cue"]["loc"], tap, stimuli["cue"]["window"]
                ):
                    info = {
                        "touch": 1,
                        "RT": current_time - start_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    if self.options.get("cue_touch_enabled", False):
                        break
        return info

    def _show_sample(self, stimuli, timing, show_cue=False):
        self.screen.fill(self.background)
        if show_cue:
            self.draw_stimulus(**stimuli["cue"])
        self.draw_stimulus(**stimuli["target"])
        for distractor in stimuli["distractors"]:
            self.draw_stimulus(**distractor)
        self.flip()

        start_time = current_time = time.time()
        info = {"touch": 0, "RT": 0}
        while (current_time - start_time) < timing["sample_duration"]:
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
                    info.update(
                        {"RT": current_time - start_time, "x": tap[0], "y": tap[1]}
                    )
                    if info["touch"] == 0:
                        info["touch"] = 1
                        info["tapped"] = stimuli["target"]["name"]
                    else:
                        info["touch"] = 3

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
                    break
                else:
                    info = {
                        "touch": 2,
                        "RT": current_time - start_time,
                        "x": tap[0],
                        "y": tap[1],
                    }

                    for distractor in stimuli["distractors"]:
                        if self.was_tapped(
                            distractor["loc"], tap, distractor["window"]
                        ):
                            info["tapped"] = distractor["name"]
                            break
                    else:
                        info["tapped"] = "outside"
                        if self.options.get('ignore_outside',False):
                            continue

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
                    break
        # else: #no response?
        self.screen.fill(self.background)
        self.flip()
        return info

    def run(self):
        self.initialize()
        trial = 0
        self.running = True
        self.start_time = time.time()
        while self.running:
            self.update_info(trial)
            self._run_intertrial_interval()
            if not self.running: return

            # initialize trial parameters
            condition = self.get_condition()
            if condition is None:
                break

            stimuli = {
                stimulus: self.get_item(self.conditions[condition][stimulus])
                for stimulus in ["cue", "target", "correct", "incorrect"]
            }
            stimuli["distractors"] = [
                self.get_item(distractor)
                for distractor in self.conditions[condition]["distractors"]
            ]
            timing = {
                f"{event}_duration": self.get_duration(event)
                for event in ["cue", "delay", "sample", "correct", "incorrect"]
            }
            if "delay_distractor" in self.conditions[condition]:
                stimuli["delay_distractor"] = self.get_item(
                    self.conditions[condition]["delay_distractor"]
                )
                timing.update(
                    {
                        event: self.get_duration(event)
                        for event in [
                            "delay_distractor_duration",
                            "delay_distractor_onset",
                        ]
                    }
                )
            else:
                stimuli["delay_distractor"] = None

            if self.options.get("push_to_start", False):
                start_result = self._start_trial()
                if start_result is None:
                    continue
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
                cue_touch=0,
                sample_touch=0,
                cue_RT=0,
                sample_RT=0,
                tapped="none",
                **timing,
            )

            # run trial
            cue_result = self._show_cue(stimuli, timing)
            if cue_result is None:
                break
            elif cue_result["touch"] == 0 and self.options.get(
                "cue_touch_enabled", False
            ):
                # If cue is exitable and no touch, do not run delay/sample.
                self.trial.data.update(
                    {
                        "cue_touch": cue_result.get("touch", 0),
                        "cue_RT": cue_result.get("RT", 0),
                        "sample_touch": 0,
                        "sample_RT": 0,
                        "tapped": "none",
                    }
                )
            else:
                if timing["delay_duration"] > 0:
                    delay_result = self._run_delay(stimuli, timing)
                else:
                    delay_result = {"touch": 0}

                if delay_result is None:
                    break
                elif delay_result.get("touch", 0) >= 0:  # no matter what
                    sample_result = self._show_sample(
                        stimuli, timing, show_cue=timing["delay_duration"] < 0
                    )
                    if sample_result is None:
                        break
                    self.trial.data.update(
                        {
                            "cue_touch": cue_result.get("touch", 0),
                            "cue_RT": cue_result.get("RT", 0),
                            "sample_touch": sample_result.get("touch", 0),
                            "sample_RT": sample_result.get("RT", 0),
                            "tapped": sample_result.get("tapped", "none"),
                        }
                    )
            outcome = self.trial.data["sample_touch"]

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
