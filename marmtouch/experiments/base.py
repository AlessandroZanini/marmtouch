import marmtouch.util as util

from pathlib import Path 
import time
import random

import RPi.GPIO as GPIO
import pygame
import yaml 

class Experiment:
    """ Base Class for designing experiments in marmtouch

    Parameters
    ----------
    data_dir: Path or path-like, required
        if set to None, nothing will be saved.  This needs to be accounted for in self.run
    params: dict, required
        All parameters for the experiment. Must contain 'timing', 'conditions' and 'background' fields (see below)

    Notes
    -----
    [1] You must define self.screen and self.info_screen in self.run for self.flip to function
    [2] draw_stimulus does not automatically flip the screen to prevent unnecessary updating when multiple items are drawn.  self.flip must be called when screen is to be updated.
    """

    keys = ['trial','trial_start_time','condition']
    sep = ','
    info_background = (0,0,0)
    def __init__(self,data_dir,params,TTLout={'reward':11,'sync':16},camera=True,camera_preview=False,camera_preview_window=(0,600,320,200)):
        if data_dir is None:
            self.data_dir = None
            self.logger = util.getLogger()
        else:
            data_dir = Path(data_dir)
            if not data_dir.is_dir():
                data_dir.mkdir()
            self.data_dir = data_dir
            self.behdata_path = self.data_dir/'behaviour.csv'
            self.logger_path = self.data_dir/'marmtouch.log'
            self.events_path = self.data_dir/'events.yaml'
            self.params_path = self.data_dir/'params.yaml'

            with open(self.params_path.as_posix(), 'w') as f:
                yaml.dump(params, f)
            with open(self.behdata_path.as_posix(), 'w') as f:
                f.write(",".join(self.keys)+'\n')
            self.logger = util.getLogger(self.logger_path.as_posix())
        self.camera_preview = camera_preview
        self.camera_preview_window = camera_preview_window
        if camera:
            self.camera = util.setup_camera()
        else:
            self.camera = None
        
        self.TTLout = {k: util.TTL(v) for k, v in TTLout.items()}

        self.params = params
        self.timing = params['timing']
        self.conditions = params['conditions']
        self.background = params['background']

        self.behdata = []
        self.events = []

        util.setup_screen()
        self.logger.info(f'experiment initialized')
    
    def get_duration(self, name):
        duration = self.timing[name]
        if isinstance(duration, (int, float)):
            return duration
        else:
            return random.choice(duration)

    def graceful_exit(self):
        GPIO.cleanup()
        if self.camera is not None and self.camera.recording:
            self.camera.stop_recording()
        if self.camera is not None and self.camera_preview:
            self.camera.stop_preview()
        if self.data_dir is not None:
            with open(self.events_path.as_posix(), 'w') as f:
                yaml.dump(self.events, f)
        self.running = False
        pygame.quit()
    
    def parse_events(self):
        event_time = time.time() - self.start_time
        event_stack = []
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouseX, mouseY = pygame.mouse.get_pos()
                event_stack.append({'type':'mouse_down','time':event_time,'mouseX':mouseX,'mouseY':mouseY})
                if mouseX<300:
                    self.graceful_exit()
            if event.type == pygame.QUIT:
                event_stack.append({'type':'QUIT','time':event_time})
                self.graceful_exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    event_stack.append({'type':'key_down','time':event_time,'key':'escape'})
                    self.graceful_exit()
        self.events.extend(event_stack)
        return event_stack
    
    @staticmethod
    def get_first_tap(event_stack):
        taps = []
        for event in event_stack:
            if event['type'] == 'mouse_down':
                taps.append((event['mouseX'],event['mouseY']))
        if taps:
            return taps[0] #return the first tap in the queue - is this necessary?
        else:
            return None

    def dump_trialdata(self,trialdata):
        with open(self.behdata_path.as_posix(),'a') as f:
            f.write(self.sep.join([str(trialdata[key]) for key in self.keys])+'\n')
        self.behdata.append(trialdata)

    def initialize(self):
        pygame.init()
        pygame.mouse.set_visible(1)
        pygame.mouse.set_cursor((8,8),(0,0),(0,0,0,0,0,0,0,0),(0,0,0,0,0,0,0,0))
        self.screen = pygame.display.set_mode((0,0),pygame.FULLSCREEN)
        self.info_screen = pygame.Surface((350,800))
        self.screen.fill(self.background)
        self.info_screen.fill(self.info_background)
        self.font = pygame.font.Font(None,20)
        self.flip()

        if self.camera_preview:
            self.camera.start_preview(fullscreen=False,window=self.camera_preview_window)

    def draw_stimulus(self,**params):
        """ Draws stimuli on screen
        
        Draws stimuli on screen using pygame using parameters provided.
        Must manually call pygame.display.update() after drawing all stimuli.
        Use self.screen.fill(self.background) to clear the screen

        """
        if params['type'] == 'circle':
            pygame.draw.circle(self.screen, params['color'], params['loc'], params['radius'])
    def flip(self):
        self.screen.blit(self.info_screen,(0,0))
        pygame.display.update()
