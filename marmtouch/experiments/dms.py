from marmtouch.experiments.base import Experiment
from marmtouch.experiments.mixins.task_components.delay import DelayMixin
from marmtouch.util.parse_csv import parse_csv

from collections import Counter
from itertools import product, combinations
import random
import time

import pygame

class DMS(Experiment, DelayMixin):
    keys = 'trial','trial_start_time','condition','sample_touch','sample_RT','test_touch','test_RT','sample_duration','delay_duration','test_duration','match_img','nonmatch_img'
    name = 'DMS'
    info_background = (0,0,0)

    def _show_sample(self,stimuli,timing):
        sample = stimuli['sample']

        self.screen.fill(self.background)
        self.draw_stimulus(**sample)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < timing['sample_duration']:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is not None:
                if self.was_tapped(sample['loc'], tap, sample['window']):
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
        return info

    def _show_test(self,stimuli,timing,show_distractor=True,show_sample=False):
        sample, target, distractor = stimuli['sample'], stimuli['target'], stimuli['distractor']
        self.screen.fill(self.background)
        self.draw_stimulus(**target)
        if show_distractor: self.draw_stimulus(**distractor)
        if show_sample: self.draw_stimulus(**sample)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < timing['test_duration']:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if self.was_tapped(target['loc'], tap, target['window']):
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    #reward and show correct for correct duration
                    self.screen.fill(self.background)
                    self.draw_stimulus(**target)
                    self.flip()
                    self.good_monkey()
                    start_time = time.time()
                    while (time.time()-start_time) < timing['correct_duration']: 
                        self.parse_events()
                    #clear screen and exit
                    self.screen.fill(self.background)
                    self.flip()
                    break
                elif self.was_tapped(distractor['loc'], tap, distractor['window']):
                    info = {'touch':2, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    #show incorrect for incorrect duration
                    self.screen.fill(self.background)
                    self.flip()
                    start_time = time.time()
                    while (time.time()-start_time) < timing['incorrect_duration']:
                        self.parse_events()
                    #clear screen and exit
                    self.screen.fill(self.background)
                    self.flip()
                    break
                else: # if tapped outside of the two items
                    continue
        #else: #no response?
        return info

    def get_stimuli(self, trial, condition):
        ## GET STIMULI
        if self.options.get('method','itemfile')=='itemfile':
            idx = trial%len(self.items)
            match_name, nonmatch_name = self.items[idx]['A'], self.items[idx]['B']
            match_stim, nonmatch_stim = dict(type='image',path=match_name), dict(type='image',path=nonmatch_name)
        else:
            match_name, nonmatch_name = random.choice(list(combinations(self.items.keys(), 2)))
            match_stim, nonmatch_stim = self.items[match_name], self.items[nonmatch_name]
        sample = self.get_item(**match_stim,**self.conditions[condition]['sample'])
        match = self.conditions[condition]['match']
        if match is not None:
            match = self.get_item(**match_stim,**match)
        nonmatch = self.conditions[condition]['nonmatch']
        if nonmatch is not None:
            nonmatch = self.get_item(**nonmatch_stim,**nonmatch)
        if self.options.get('match', True):
            stimuli = {'sample': sample, 'target': match, 'distractor': nonmatch}
        else:
            stimuli = {'sample': sample, 'target': nonmatch, 'distractor': match}
        return stimuli, match_name, nonmatch_name

    def run(self):
        self.initialize()
        if self.options.get('method','itemfile')=='itemfile':
            self.items = parse_csv(self.items)

        delay_times = [self.timing['delay']] if isinstance(self.timing['delay'], (int, float)) else self.timing['delay']
        combinations = product(delay_times, self.conditions.keys())
        self.info = {(condition, delay): Counter() for (delay, condition) in combinations}

        self.itemid = trial = 0
        self.running = True
        self.start_time = time.time()
        while self.running:
            self.update_info(trial)
            
            #iti
            start_time = time.time()
            while time.time()-start_time<self.options.get('iti',5):
                self.parse_events()
                if not self.running:
                    return
            if not self.running:
                return

            #initialize trial parameters
            if self.blocks is None:
                condition = random.choice(list(self.conditions.keys()))
            else:
                condition = self.get_condition()

            stimuli, match_img, nonmatch_img = self.get_stimuli(self.itemid, condition)

            ## GET TIMING INFO
            timing = {
                f'{epoch}_duration': self.get_duration(epoch) 
                for epoch in ['sample', 'delay', 'test', 'correct', 'incorrect']
            }
            trial_start_time = time.time() - self.start_time
            trialdata = dict(
                trial=trial,trial_start_time=trial_start_time,condition=condition,
                sample_touch=0,sample_RT=0,test_touch=0,test_RT=0,
                match_img=match_img,nonmatch_img=nonmatch_img,
                **timing
            )

            if self.options.get('push_to_start',True):
                start_result = self._start_trial()
                if start_result is None: continue
            self.TTLout['sync'].pulse(.1)
            if self.camera is not None:
                self.camera.start_recording((self.data_dir/f'{trial}.h264').as_posix())

            #run trial
            sample_result = self._show_sample(stimuli, timing)
            if sample_result is None:
                break
            if sample_result['touch'] >= 0: #no matter what
                if timing['delay_duration'] < 0: #if delay duration is negative, skip delay and keep the sample on during test phase
                    delay_result = dict(touch=0,RT=0)
                else:
                    delay_result = self._run_delay(stimuli, timing)
                if delay_result is None:
                    break
                if delay_result.get('touch',0) >= 0: #no matter what
                    test_result = self._show_test(
                        stimuli, 
                        timing,
                        show_distractor = stimuli['distractor'] is not None, 
                        show_sample = timing['delay_duration'] < 0
                    )
                    if test_result is None:
                        break
                    trialdata.update({
                        'sample_touch': sample_result.get('touch',0),
                        'sample_RT': sample_result.get('RT',0),
                        'test_touch': test_result.get('touch',0),
                        'test_RT': test_result.get('RT',0)
                    })
            outcome = trialdata['test_touch']

            #wipe screen
            self.screen.fill(self.background)
            self.flip()

            if self.camera is not None:
                self.camera.stop_recording()
            self.dump_trialdata(trialdata)
            trial += 1
            self.itemid += 1
            self.info[condition, timing['delay_duration']][outcome] += 1
            if self.blocks is not None:
                self.update_condition_list(correct=(outcome==1), trialunique=self.active_block.get('repeat_items', True))

    def update_info(self,trial):
        info = f"{self.params['monkey']} {self.params['task']} Trial#{trial}\n"
        for (condition, delay), condition_info in self.info.items():
            info += f"Condition {condition}, Delay: {delay}: {condition_info[1]: 3d} correct, {condition_info[2]: 3d} incorrect\n"
        overall = sum(self.info.values(),Counter())
        info += f"Overall: {overall[1]: 3d} correct, {overall[2]: 3d} incorrect, {overall[0]: 3d} no response\n"
        
        self.info_screen.fill(self.info_background)
        for idx, line in enumerate(info.splitlines()):
            txt = self.font.render(line,True,pygame.Color('GREEN'))
            txt = pygame.transform.rotate(txt,90)
            self.info_screen.blit(txt, (idx*30,30))

        self.info_screen.blit(self.session_txt, self.session_txt_rect)

        self.flip()
