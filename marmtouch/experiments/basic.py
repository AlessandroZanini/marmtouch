from marmtouch.experiments.base import Experiment

from collections import Counter
import random
import time
from pathlib import Path

import pygame


class Basic(Experiment):
    keys = 'trial','trial_start_time','condition','target_touch','target_RT','target_duration','correct_duration','incorrect_duration'
    name = 'Basic'
    info_background = (0,0,0)

    def _show_target(self,stimuli,timing,rel_tol=2):

        tolerance = stimuli['target']['radius']*rel_tol

        self.screen.fill(self.background)
        self.draw_stimulus(**stimuli['target'])

        distractors = stimuli.get('distractors')
        if distractors is not None:
            for distractor in distractors:
                self.draw_stimulus(**distractor)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time)<timing['target_duration']:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if abs(stimuli['target']['loc'][0]-tap[0])<tolerance and abs(stimuli['target']['loc'][1]-tap[1])<tolerance:
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    if timing['correct_duration']:
                        self.screen.fill(self.background)
                        self.draw_stimulus(**stimuli['correct'])
                        self.flip()
                        self.TTLout['reward'].pulse(.2,n_pulses=1,interpulse_interval=1)
                        start_time = time.time()
                        while (time.time()-start_time) < timing['correct_duration']: 
                            self.parse_events()
                    else:
                        self.good_monkey()
                    
                    self.screen.fill(self.background)
                    self.flip()
                    break
                else:
                    info = {'touch':2, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    if timing['incorrect_duration']:
                        self.screen.fill(self.background)
                        self.draw_stimulus(**stimuli['incorrect'])
                        self.flip()
                        start_time = time.time()
                        while (time.time()-start_time) < timing['incorrect_duration']: 
                            self.parse_events()
                    self.screen.fill(self.background)
                    self.flip()
                    break
        return info

    def run(self):
        self.initialize()
        self.info = {condition: Counter() for condition in self.conditions.keys()}

        trial = 0
        self.running = True
        self.start_time = time.time()
        while self.running:
            self.update_info(trial)
            
            #iti
            start_time = time.time()
            while time.time()-start_time<3:
                self.parse_events()
                if not self.running: return
            
            #initialize trial parameters
            condition = random.choice(list(self.conditions.keys()))
            stimuli = {stimulus: self.get_item(self.conditions[condition][stimulus]) for stimulus in ['target','correct','incorrect']}

            distractors = self.conditions[condition].get('distractors')
            if distractors is not None:
                stimuli['distractors'] = [self.get_item(distractor) for distractor in distractors]

            timing = {f"{event}_duration": self.get_duration(event) for event in ['target','correct','incorrect']}
            trial_start_time = time.time() - self.start_time
            trialdata = dict(trial=trial,trial_start_time=trial_start_time,condition=condition,target_touch=0,target_RT=0,**timing)

            self.TTLout['sync'].pulse(.1)
            if self.camera is not None:
                self.camera.start_recording((self.data_dir/f'{trial}.h264').as_posix())

            #run trial
            target_result = self._show_target(stimuli, timing)
            if target_result is None: return
                
            trialdata.update({
                'target_touch': target_result.get('touch',0),
                'target_RT': target_result.get('RT',0),
            })

            #wipe screen
            self.screen.fill(self.background)
            self.flip()

            if self.camera is not None:
                self.camera.stop_recording()
            self.dump_trialdata(trialdata)
            trial += 1
            self.info[condition][trialdata['target_touch']] += 1