from marmtouch.experiments.base import Experiment

from collections import Counter
import random
import time
from pathlib import Path

import pygame


class Basic(Experiment):
    keys = 'trial','trial_start_time','condition','target_touch','target_RT','target_duration'
    name = 'Memory'
    info_background = (0,0,0)

    def _show_target(self,condition,target_duration,correct_duration,incorrect_duration,rel_tol=2):
        target = self.conditions[condition]['target']
        correct = self.conditions[condition]['correct']
        incorrect = self.conditions[condition]['incorrect']

        tolerance = target['radius']*rel_tol

        self.screen.fill(self.background)
        self.draw_stimulus(**target)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time)<target_duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if abs(target['loc'][0]-tap[0])<tolerance and abs(target['loc'][1]-tap[1])<tolerance:
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    if correct_duration:
                        self.screen.fill(self.background)
                        self.draw_stimulus(**correct)
                        self.flip()
                        self.TTLout['reward'].pulse(.2,n_pulses=1,interpulse_interval=1)
                        start_time = time.time()
                        while (time.time()-start_time) < correct_duration: 
                            self.parse_events()
                    else:
                        self.TTLout['reward'].pulse(.2,n_pulses=1,interpulse_interval=1)
                    
                    self.screen.fill(self.background)
                    self.flip()
                    break
                else:
                    info = {'touch':2, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    if incorrect_duration:
                        self.screen.fill(self.background)
                        self.draw_stimulus(**incorrect)
                        self.flip()
                        start_time = time.time()
                        while (time.time()-start_time) < incorrect_duration: 
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
            target_duration, correct_duration, incorrect_duration = self.get_duration('target'), self.get_duration('correct'), self.get_duration('incorrect')
            trial_start_time = time.time() - self.start_time
            trialdata = dict(trial=trial,trial_start_time=trial_start_time,condition=condition,target_touch=0,target_RT=0,target_duration=target_duration)

            self.TTLout['sync'].pulse(.1)
            if self.camera is not None:
                self.camera.start_recording((self.data_dir/f'{trial}.h264').as_posix())

            #run trial
            target_result = self._show_target(condition, target_duration, correct_duration, incorrect_duration)
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
