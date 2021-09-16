from marmtouch.experiments.base import Experiment

from collections import Counter
import random
import time
from pathlib import Path

import pandas as pd
import pygame

class DMS(Experiment):
    keys = 'trial','trial_start_time','condition','sample_touch','sample_RT','test_touch','test_RT','sample_duration','delay_duration','test_duration','imga','imgb'
    name = 'DMS'
    info_background = (0,0,0)

    def _run_delay(self,duration):
        """ Run a delay based for provided duration. Returns last touch during delay period if there was one. """
        self.screen.fill(self.background)
        self.flip()
        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time - start_time) < duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is not None:
                info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
        return info

    def _show_sample(self,sample,duration,rel_tol=2):
        # sample = self.items[self.conditions[condition]['sample']]
        tolerance = sample['radius']*rel_tol

        self.screen.fill(self.background)
        self.draw_stimulus(**sample)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is not None:
                if abs(sample['loc'][0]-tap[0])<tolerance and abs(sample['loc'][1]-tap[1])<tolerance:
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
        return info

    def _show_test(self,match,nonmatch,test_duration,correct_duration,incorrect_duration,rel_tol=2,sample=None):
        # match = self.items[self.conditions[condition]['match']]
        # nonmatch = self.items[self.conditions[condition]['nonmatch']]
        tolerance = match['radius']*rel_tol

        self.screen.fill(self.background)
        for item in [match, nonmatch]:
            self.draw_stimulus(**item)
        if sample is not None:
            self.draw_stimulus(**sample)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < test_duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if abs(match['loc'][0]-tap[0])<tolerance and abs(match['loc'][1]-tap[1])<tolerance:
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    #reward and show correct for correct duration
                    self.screen.fill(self.background)
                    self.draw_stimulus(**match)
                    self.flip()
                    self.good_monkey()
                    start_time = time.time()
                    while (time.time()-start_time) < correct_duration: 
                        self.parse_events()
                    #clear screen and exit
                    self.screen.fill(self.background)
                    self.flip()
                    break
                else:
                    info = {'touch':2, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    #show incorrect for incorrect duration
                    self.screen.fill(self.background)
                    self.flip()
                    start_time = time.time()
                    while (time.time()-start_time) < incorrect_duration:
                        self.parse_events()
                    #clear screen and exit
                    self.screen.fill(self.background)
                    self.flip()
                    break
        #else: #no response?
        return info

    def run(self):
        self.initialize()
        # self.stimuli = pd.read_csv(self.items, index_col=0)
        self.stimuli = self.parse_csv(self.items)

        self.info = {condition: Counter() for condition in self.conditions.keys()}

        trial = 0
        self.running = True
        self.start_time = time.time()
        while self.running:
            self.update_info(trial)
            
            #iti
            start_time = time.time()
            while time.time()-start_time<5:
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
            
            ## GET STIMULI
            idx = trial%len(self.stimuli)
            imga, imgb = self.stimuli[idx]['A'], self.stimuli[idx]['A']
            sample = self.get_image_stimulus(imga,**self.conditions[condition]['sample'])
            match = self.get_image_stimulus(imga,**self.conditions[condition]['match'])
            nonmatch = self.get_image_stimulus(imgb,**self.conditions[condition]['nonmatch'])

            ## GET TIMING INFO
            sample_duration, delay_duration, test_duration = self.get_duration('sample'), self.get_duration('delay'), self.get_duration('test')
            trial_start_time = time.time() - self.start_time
            trialdata = dict(
                trial=trial,trial_start_time=trial_start_time,condition=condition,
                sample_touch=0,test_touch=0,sample_RT=0,test_RT=0,sample_duration=sample_duration,
                delay_duration=delay_duration,test_duration=test_duration,imga=imga,imgb=imgb)

            self.TTLout['sync'].pulse(.1)
            self.camera.start_recording((self.data_dir/f'{trial}.h264').as_posix())

            #run trial
            sample_result = self._show_sample(sample, sample_duration)
            if sample_result is None:
                break
            if sample_result['touch'] >= 0: #no matter what
                if delay_duration < 0: #if delay duration is negative, skip delay and keep the sample on during test phase
                    delay_result = dict(touch=0,RT=0)
                else:
                    delay_result = self._run_delay(delay_duration)
                    sample = None
                if delay_result is None:
                    break
                if delay_result.get('touch',0) >= 0: #no matter what
                    test_result = self._show_test(
                        match, nonmatch, test_duration, 
                        self.get_duration('correct'), 
                        self.get_duration('incorrect'), 
                        sample=sample
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

            self.camera.stop_recording()
            self.dump_trialdata(trialdata)
            trial += 1
            self.info[condition][outcome] += 1
            if self.blocks is not None:
                self.update_condition_list(correct=(outcome==1))

    def update_info(self,trial):
        info = f"{self.params['monkey']} {self.params['task']} Trial#{trial}\n"
        for condition, condition_info in self.info.items():
            info += f"Condition {condition}: {condition_info[1]: 3d} correct, {condition_info[2]: 3d} incorrect\n"
        overall = sum(self.info.values(),Counter())
        info += f"Overall: {overall[1]: 3d} correct, {overall[2]: 3d} incorrect, {overall[0]: 3d} no response\n"
        
        self.info_screen.fill(self.info_background)
        for idx, line in enumerate(info.splitlines()):
            txt = self.font.render(line,True,pygame.Color('GREEN'))
            txt = pygame.transform.rotate(txt,90)
            self.info_screen.blit(txt, (idx*30,30))
        self.flip()