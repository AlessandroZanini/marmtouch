from marmtouch.experiments.base import Experiment

from collections import Counter
from itertools import product
import random
import time

import pygame

class Memory(Experiment):
    keys = 'trial','trial_start_time','condition','cue_touch','cue_RT','sample_touch','sample_RT','cue_duration','delay_duration','sample_duration','correct_duration','incorrect_duration','tapped'
    name = 'Memory'
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

    def _show_cue(self,stimuli,timing):
        self.screen.fill(self.background)
        self.draw_stimulus(**stimuli['cue'])
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < timing['cue_duration']:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is not None:
                if self.was_tapped(stimuli['cue']['loc'], tap, stimuli['cue']['window']):
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    if self.options.get('cue_touch_enabled',False): break
        return info

    def _show_sample(self,stimuli,timing,show_cue=False):
        self.screen.fill(self.background)
        if show_cue:
            self.draw_stimulus(**stimuli['cue'])
        self.draw_stimulus(**stimuli['target'])
        for distractor in stimuli['distractors']:
            self.draw_stimulus(**distractor)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < timing['sample_duration']:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is None:
                continue
            else:
                if self.was_tapped(stimuli['target']['loc'], tap, stimuli['target']['window']):
                    info.update({'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]})
                    if info['touch']==0:
                        info['touch'] = 1
                        info['tapped'] = stimuli['target']['name']
                    else:
                        info['touch'] = 3

                    if timing['correct_duration']:
                        self.screen.fill(self.background)
                        self.draw_stimulus(**stimuli['correct'])
                        self.flip()
                        self.good_monkey()
                        start_time = time.time()
                        while (time.time()-start_time) < timing['correct_duration']: 
                            self.parse_events()
                    else:
                        self.good_monkey()
                    break
                else:
                    info = {'touch':2, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}

                    for distractor in stimuli['distractors']:
                        if self.was_tapped(distractor['loc'], tap, distractor['window']):
                            info['tapped'] = distractor['name']
                            break
                    else:
                        info['tapped'] = 'outside'

                    if self.options.get('ignore_incorrect', False): 
                        continue
                    elif self.options.get('reward_incorrect', False): 
                        self.good_monkey()
                    elif timing['incorrect_duration']:
                        self.screen.fill(self.background)
                        self.draw_stimulus(**stimuli['incorrect'])
                        self.flip()
                        start_time = time.time()
                        while (time.time()-start_time) < timing['incorrect_duration']: 
                            self.parse_events()
                    break
        #else: #no response?
        self.screen.fill(self.background)
        self.flip()
        return info

    def run(self):
        self.initialize()

        delay_times = [self.timing['delay']] if isinstance(self.timing['delay'], (int, float)) else self.timing['delay']
        combinations = product(delay_times, self.conditions.keys())
        self.info = {(condition, delay): Counter() for (delay, condition) in combinations}

        trial = 0
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

            stimuli = {stimulus: self.get_item(self.conditions[condition][stimulus]) for stimulus in ['cue','target','correct','incorrect']}
            stimuli['distractors'] = [self.get_item(distractor) for distractor in self.conditions[condition]['distractors']]

            timing = {f"{event}_duration": self.get_duration(event) for event in ['cue','delay','sample','correct','incorrect']}
            trial_start_time = time.time() - self.start_time
            trialdata = dict(
                trial=trial,trial_start_time=trial_start_time,
                condition=condition,cue_touch=0,sample_touch=0,
                cue_RT=0,sample_RT=0,tapped='none',**timing
            )

            if self.options.get('push_to_start',False):
                start_result = self._start_trial()
                if start_result is None: continue
            self.TTLout['sync'].pulse(.1)
            self.camera.start_recording((self.data_dir/f'{trial}.h264').as_posix())

            #run trial
            cue_result = self._show_cue(stimuli, timing)
            if cue_result is None:
                break
            elif cue_result['touch']==0 and self.options.get('cue_touch_enabled', False):
                #If cue is exitable and no touch, do not run delay/sample.
                trialdata.update({
                        'cue_touch': cue_result.get('touch',0),
                        'cue_RT': cue_result.get('RT',0),
                        'sample_touch': 0,
                        'sample_RT': 0,
                        'tapped': 'none'
                })
            else:
                if timing['delay_duration'] > 0:
                    delay_result = self._run_delay(timing['delay_duration'])
                else:
                    delay_result = {'touch':0}

                if delay_result is None:
                    break
                elif delay_result.get('touch',0) >= 0: #no matter what
                    sample_result = self._show_sample(stimuli, timing, show_cue=timing['delay_duration']<0)
                    if sample_result is None:
                        break
                    trialdata.update({
                        'cue_touch': cue_result.get('touch',0),
                        'cue_RT': cue_result.get('RT',0),
                        'sample_touch': sample_result.get('touch',0),
                        'sample_RT': sample_result.get('RT',0),
                        'tapped': sample_result.get('tapped','none')
                    })
            outcome = trialdata['sample_touch']

            #wipe screen
            self.screen.fill(self.background)
            self.flip()

            self.camera.stop_recording()
            self.dump_trialdata(trialdata)
            trial += 1
            self.info[condition, timing['delay_duration']][outcome] += 1
            if self.blocks is not None:
                self.update_condition_list(correct=(outcome==1))

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
