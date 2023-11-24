import random
import time
from collections import Counter
from itertools import combinations, product

import pygame

from marmtouch.experiments.base import Experiment
from marmtouch.experiments.mixins.task_components.delay import DelayMixin
from marmtouch.experiments.trialrecord import TrialRecord
from marmtouch.experiments.util.events import get_first_tap, was_tapped
from marmtouch.util.parse_csv import parse_csv


class DMS(Experiment, DelayMixin):
    keys = (
        "trial",
        "trial_start_time",
        "condition",
        "sample_touch",
        "sample_RT",
        "test_touch",
        "test_RT",
        "sample_duration",
        "delay_duration",
        "test_duration",
        "correct_duration",
        "incorrect_duration",
        "match_img",
        "nonmatch_img",
        "sync_onset",
        "start_stimulus_onset",
        "start_stimulus_offset",
    )
    name = "DMS"
    info_background = (0, 0, 0)
    info_breakdown_keys = {
        "Condition": "condition",
        "Delay": "delay_duration",
    }
    outcome_key = "test_touch"

    def _show_sample(self, stimuli, timing):
        sample = stimuli["sample"]

        self.screen.fill(self.background)
        self.draw_stimulus(**sample)
        self.flip()

        info = {"touch": 0, "RT": 0}
        self.clock.wait(timing["sample_duration"])
        while self.clock.waiting():
            tap = get_first_tap(self.event_manager.parse_events())
            if not self.running:
                return
            if tap is not None:
                if was_tapped(sample["loc"], tap, sample["window"]):
                    info = {
                        "touch": 1,
                        "RT": self.clock.elapsed_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
        return info

    def _show_test(self, stimuli, timing, show_distractor=True, show_sample=False):
        sample, target, distractor = (
            stimuli["sample"],
            stimuli["target"],
            stimuli["distractor"],
        )
        self.screen.fill(self.background)
        self.draw_stimulus(**target)
        if show_distractor:
            self.draw_stimulus(**distractor)
        if show_sample:
            self.draw_stimulus(**sample)
        self.flip()

        info = {"touch": 0, "RT": 0}
        self.clock.wait(timing["test_duration"])
        while self.clock.waiting():
            tap = get_first_tap(self.event_manager.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if was_tapped(target["loc"], tap, target["window"]):
                    info = {
                        "touch": 1,
                        "RT": self.clock.elapsed_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    # reward and show correct for correct duration
                    self.screen.fill(self.background)
                    self.draw_stimulus(**target)
                    self.flip()
                    self.good_monkey()
                    self.clock.wait(timing["correct_duration"])
                    while self.clock.waiting():
                        self.event_manager.parse_events()
                    # clear screen and exit
                    self.screen.fill(self.background)
                    self.flip()
                    break
                elif was_tapped(distractor["loc"], tap, distractor["window"]):
                    info = {
                        "touch": 2,
                        "RT": self.clock.elapsed_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    # show incorrect for incorrect duration
                    self.screen.fill(self.background)
                    self.flip()
                    self.clock.wait(timing["incorrect_duration"])
                    while self.clock.waiting():
                        self.event_manager.parse_events()
                    # clear screen and exit
                    self.screen.fill(self.background)
                    self.flip()
                    break
                else:  # if tapped outside of the two items
                    continue
        # else: #no response?
        return info

    def get_stimuli(self, trial, condition):
        ## GET STIMULI
        if self.options.get("method", "itemfile") == "itemfile":
            idx = trial % len(self.items)
            match_name, nonmatch_name = self.items[idx]["A"], self.items[idx]["B"]
            match_stim, nonmatch_stim = dict(type="image", path=match_name), dict(
                type="image", path=nonmatch_name
            )
        else:
            match_name, nonmatch_name = random.choice(
                list(combinations(self.items.keys(), 2))
            )
            match_stim, nonmatch_stim = (
                self.items[match_name],
                self.items[nonmatch_name],
            )
        sample = self.get_item(**match_stim, **self.conditions[condition]["sample"])
        match = self.conditions[condition]["match"]
        if match is not None:
            match = self.get_item(**match_stim, **match)
        nonmatch = self.conditions[condition]["nonmatch"]
        if nonmatch is not None:
            nonmatch = self.get_item(**nonmatch_stim, **nonmatch)
        if self.options.get("match", True):
            stimuli = {"sample": sample, "target": match, "distractor": nonmatch}
        else:
            stimuli = {"sample": sample, "target": nonmatch, "distractor": match}
        return stimuli, match_name, nonmatch_name

    def get_timing(self, condition):
        timing = {
            f"{event}_duration": self.get_duration(event)
            for event in ["sample", "delay", "test", "correct", "incorrect"]
        }
        return timing

    def run(self):
        self.initialize()
        if self.options.get("method", "itemfile") == "itemfile":
            self.items = parse_csv(self.items)

        self.itemid = trial = 0
        self.running = True
        while self.running:
            self.update_info(trial)
            self._run_intertrial_interval()
            if not self.running:
                return

            # initialize trial parameters
            condition = self.get_condition()
            if condition is None:
                break

            stimuli, match_img, nonmatch_img = self.get_stimuli(self.itemid, condition)
            timing = self.get_timing(condition)

            if self.options.get("push_to_start", True):
                start_result = self._start_trial()
                if start_result is None:
                    continue
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
                sample_touch=0,
                sample_RT=0,
                test_touch=0,
                test_RT=0,
                match_img=match_img,
                nonmatch_img=nonmatch_img,
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
            sample_result = self._show_sample(stimuli, timing)
            if sample_result is None:
                break
            if sample_result["touch"] >= 0:  # no matter what
                if (
                    timing["delay_duration"] < 0
                ):  # if delay duration is negative, skip delay and keep the sample on during test phase
                    delay_result = dict(touch=0, RT=0)
                else:
                    delay_result = self._run_delay(stimuli, timing)
                if delay_result is None:
                    break
                if delay_result.get("touch", 0) >= 0:  # no matter what
                    test_result = self._show_test(
                        stimuli,
                        timing,
                        show_distractor=stimuli["distractor"] is not None,
                        show_sample=timing["delay_duration"] < 0,
                    )
                    if test_result is None:
                        break
                    self.trial.data.update(
                        {
                            "sample_touch": sample_result.get("touch", 0),
                            "sample_RT": sample_result.get("RT", 0),
                            "test_touch": test_result.get("touch", 0),
                            "test_RT": test_result.get("RT", 0),
                        }
                    )
            outcome = self.trial.data["test_touch"]

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
            self.itemid += 1
            self.update_condition_list(
                outcome,
                trialunique=self.active_block.get("repeat_items", True),
            )

    def _test_trial(self, test):
        self._setup_test_trial(test)
        self.update_info(test['trial'])
        stimuli, match_img, nonmatch_img = self.get_stimuli(test['itemid'], test['condition'])
        timing = self.get_timing(test['condition'])
        # run trial
        sample_result = self._show_sample(stimuli, timing)
        if sample_result is None:
            break
        if sample_result["touch"] >= 0:  # no matter what
            if (timing["delay_duration"] < 0):  
                # if delay duration is negative, skip delay and
                # keep the sample on during test phase
                delay_result = dict(touch=0, RT=0)
            else:
                delay_result = self._run_delay(stimuli, timing)
            if delay_result is None:
                break
            if delay_result.get("touch", 0) >= 0:  # no matter what
                test_result = self._show_test(
                    stimuli,
                    timing,
                    show_distractor=stimuli["distractor"] is not None,
                    show_sample=timing["delay_duration"] < 0,
                )
                if test_result is None:
                    break
        # wipe screen
        self.screen.fill(self.background)
        self.flip()
