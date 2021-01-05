from marmtouch.experiments.base import Experiment

from collections import Counter
import random
import time
from pathlib import Path

import pygame

class Memory(Experiment):
    keys = 'trial','trial_start_time','condition','cue_touch','cue_RT','sample_touch','sample_RT','cue_duration','delay_duration','sample_duration'
    name = 'Memory'
    info_background = (0,0,0)
    def _run_delay(self,condition,duration):
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

    def _show_cue(self,condition,duration,rel_tol=2):
        cue = self.conditions[condition]['cue']
        tolerance = cue['radius']*rel_tol

        self.screen.fill(self.background)
        self.draw_stimulus(**cue)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is not None:
                if abs(cue['loc'][0]-tap[0])<tolerance and abs(cue['loc'][1]-tap[1])<tolerance:
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
        return info

    def _show_sample(self,condition,sample_duration,correct_duration,incorrect_duration,rel_tol=2):
        targets = self.conditions[condition]['targets']
        cue = self.conditions[condition]['cue']
        correct = self.conditions[condition]['correct']
        incorrect = self.conditions[condition]['incorrect']

        tolerance = cue['radius']*rel_tol

        self.screen.fill(self.background)
        for target in targets:
            self.draw_stimulus(**target)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < sample_duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if abs(cue['loc'][0]-tap[0])<tolerance and abs(cue['loc'][1]-tap[1])<tolerance:
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    #reward and show correct for correct duration
                    self.screen.fill(self.background)
                    self.draw_stimulus(**correct)
                    self.flip()
                    self.TTLout['reward'].pulse(.2,n_pulses=1,interpulse_interval=1)
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
                    self.draw_stimulus(**incorrect)
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
        pygame.init()
        self.screen = pygame.display.set_mode((0,0),pygame.FULLSCREEN)
        self.info_screen = pygame.Surface((350,800))
        self.screen.fill(self.background)
        self.info_screen.fill(self.info_background)
        self.font = pygame.font.Font(None,20)
        self.flip()

        self.info = {condition: Counter() for condition in self.conditions.keys()}

        trial = 0
        self.running = True
        self.start_time = time.time()
        while self.running:
            self.update_info(trial)
            condition = random.choice(list(self.conditions.keys()))
            cue_duration, delay_duration, sample_duration = self.get_duration('cue'), self.get_duration('delay'), self.get_duration('sample')
            trial_start_time = time.time() - self.start_time
            trialdata = dict(trial=trial,trial_start_time=trial_start_time,condition=condition,cue_touch=0,sample_touch=0,cue_RT=0,sample_RT=0,cue_duration=cue_duration,delay_duration=delay_duration,sample_duration=sample_duration)

            self.TTLout['sync'].pulse(.1)
            self.camera.start_recording((self.data_dir/f'{trial}.h264').as_posix())

            cue_result = self._show_cue(condition, cue_duration)
            if cue_result is None:
                break
            if cue_result['touch'] >= 0: #no matter what
                delay_result = self._run_delay(condition, delay_duration)
                if delay_result is None:
                    break
                if delay_result.get('touch',0) >= 0: #no matter what
                    sample_result = self._show_sample(condition, sample_duration, self.get_duration('correct'), self.get_duration('incorrect'))
                    if sample_result is None:
                        break
                    trialdata.update({
                        'cue_touch': cue_result.get('touch',0),
                        'cue_RT': cue_result.get('RT',0),
                        'sample_touch': sample_result.get('touch',0),
                        'sample_RT': sample_result.get('RT',0)
                    })
            #wipe screen
            self.screen.fill(self.background)
            self.flip()

            self.camera.stop_recording()
            self.dump_trialdata(trialdata)
            trial += 1
            self.info[condition][trialdata['sample_touch']] += 1


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