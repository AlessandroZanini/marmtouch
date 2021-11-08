import marmtouch.util as util

from pathlib import Path 
import time
import random
from itertools import cycle
from collections import Counter
import warnings
import math

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
    default_reward_params = dict(duration=.2,n_pulses=1,interpulse_interval=1)
    keys = ['trial','trial_start_time','condition']
    sep = ','
    info_background = (0,0,0)
    _image_cache_max_len = 20
    system_config_path = '/home/pi/marmtouch_system_config.yaml'
    def __init__(self,data_dir,params,TTLout={'reward':11,'sync':16},camera=True,camera_preview=False,camera_preview_window=(0,600,320,200),fullscreen=True,debug_mode=False):
        system_params = yaml.safe_load(open(Path(self.system_config_path)))
        params.update(system_params)
        self.debug_mode = debug_mode
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
        self.fullscreen = fullscreen
        self.TTLout = {k: util.TTL(v) for k, v in TTLout.items()}

        self.params = params
        self.timing = params['timing']
        self.conditions = params['conditions']
        self.background = params['background']
        self.items = params['items']
        self.reward = params.get('reward', self.default_reward_params)
        self.options = params.get('options', {})
        self.images = {}

        blocks = params.get('blocks')
        if blocks is None:
            blocks = [{'conditions': list(self.conditions.keys()), 'length': len(self.conditions)}]
        self.blocks = cycle(blocks)
        self.condition_list = []

        self.behdata = []
        self.events = []

        self.logger.info(f'experiment initialized')

    def good_monkey(self):
        self.TTLout['reward'].pulse(**self.reward)

    def get_duration(self, name):
        #TODO: implement block specific timing?
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
            self.dump_trialdata()
            self.logger.info('Behavioural data dumped.')
            with open(self.events_path.as_posix(), 'w') as f:
                yaml.dump(self.events, f)
            self.logger.info(f'Event data dumped. {len(self.events)} total records.')
        self.running = False
        pygame.quit()

    def parse_events(self):
        event_time = time.time() - self.start_time
        event_stack = []
        exit_ = False
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouseX, mouseY = pygame.mouse.get_pos()
                event_stack.append({'type':'mouse_down','time':event_time,'mouseX':mouseX,'mouseY':mouseY})
                if mouseX<300:
                    exit_ = True
            if event.type == pygame.QUIT:
                event_stack.append({'type':'QUIT','time':event_time})
                exit_ = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    event_stack.append({'type':'key_down','time':event_time,'key':'escape'})
                    exit_ = True
        self.events.extend(event_stack)
        if exit_:
            self.graceful_exit()
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

    def dump_trialdata(self,trialdata={}):
        with open(self.behdata_path.as_posix(),'a') as f:
            f.write(self.sep.join([str(trialdata.get(key, 'nan')) for key in self.keys])+'\n')
        self.behdata.append(trialdata)

    def init_block(self, block_info):
        self.active_block = block_info
        method = block_info.get('method', 'random')
        conditions = block_info['conditions']
        length = block_info['length']
        self.retry_method = block_info.get('retry_method')
        self.max_retries = block_info.get('max_retries')
        self.n_retries = Counter()
        if method == 'random':
            weights = block_info.get('weights')
            self.condition_list = random.choices(conditions, weights=weights, k=length)
        elif method == 'incremental':
            condition_list = cycle(conditions)
            self.condition_list = [next(condition_list) for _ in range(length)]
        else:
            raise ValueError("'method' must be one of ['random','incremental']")

    def get_condition(self):
        if not self.condition_list:
            self.init_block(next(self.blocks))
        self.condition = self.condition_list.pop(0)
        return self.condition

    def update_condition_list(self, correct=True, trialunique=False):
        if correct:
            return

        retry_method = self.active_block.get('retry_method')
        max_retries = self.active_block.get('max_retries')
        if max_retries is not None:
            if self.n_retries[self.condition] >= max_retries:
                return
            self.n_retries[self.condition] += 1

        if retry_method is None:
            return
        elif retry_method == 'delayed':
            idx = random.randint(0, len(self.condition_list))
            self.condition_list.insert(idx, self.condition)
            if trialunique:
                warnings.warn('Delayed retry does not repeat items in trial unique experiments')
        elif retry_method == 'immediate':
            self.condition_list.insert(0, self.condition)
            if trialunique:
                self.itemid -= 1
        else:
            raise ValueError("'retry_method' must be one of [None,'delayed','immediate']")

    def initialize(self):
        pygame.init()
        if not self.debug_mode:
            util.setup_screen()
            pygame.mouse.set_visible(1)
            pygame.mouse.set_cursor((8,8),(0,0),(0,0,0,0,0,0,0,0),(0,0,0,0,0,0,0,0))
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0,0),pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((1200,800))
        self.info_screen = pygame.Surface((350,800))
        self.screen.fill(self.background)
        self.info_screen.fill(self.info_background)
        self.font = pygame.font.Font(None,30)
        self.session_font = pygame.font.Font(None,40)
        self.flip()

        if self.camera_preview:
            self.camera.start_preview(fullscreen=False,window=self.camera_preview_window)
        
        if self.data_dir is not None:
            session_name = self.data_dir.name
            if self.debug_mode:
                session_name += ' DEBUG MODE'
            text_colour = pygame.Color('RED') if self.debug_mode else pygame.Color('GREEN')
            session_txt = self.session_font.render(session_name, True, text_colour)
            self.session_txt = pygame.transform.rotate(session_txt,90)
            self.session_txt_rect = self.session_txt.get_rect(bottomleft=(0,800-30))

    @staticmethod
    def parse_csv(path):
        lines = open(path, 'r').read().splitlines()
        headers = lines.pop(0).split(',')
        data = [dict(zip(headers, line.split(','))) for line in lines]
        return data

    def draw_ngon(self, n, radius, color, loc, start_angle=0):
        x, y = loc
        start_angle = math.radians(start_angle)
        angle_delta = 2*math.pi/n
        angles = [start_angle+i*angle_delta for i in range(n)]
        points = [(x+radius*math.cos(a),y+radius*math.sin(a)) for a in angles]
        pygame.draw.polygon(self.screen, color, points)

    def draw_star(self, n, radius, color, loc, start_angle=0, inner_outer_ratio=0.5):
        x, y = loc
        n *= 2
        start_angle = math.radians(start_angle)
        angle_delta = 2*math.pi/n
        points = []
        for i in range(n):
            a = start_angle+i*angle_delta
            radius_ = radius if i%2 else radius*inner_outer_ratio
            points.append((x+radius_*math.cos(a),y+radius_*math.sin(a)))
        pygame.draw.polygon(self.screen, color, points)

    def draw_cross(self, radius, color, loc, width=1):
        x, y = loc
        pygame.draw.line(self.screen, color, (x-radius,y), (x+radius,y), width)
        pygame.draw.line(self.screen, color, (x,y-radius), (x,y+radius), width)

    def draw_stimulus(self,**params):
        """ Draws stimuli on screen
        
        Draws stimuli on screen using pygame using parameters provided.
        Must manually call pygame.display.update() after drawing all stimuli.
        Use self.screen.fill(self.background) to clear the screen
        """
        if params['type'] == 'circle':
            pygame.draw.circle(self.screen, params['color'], params['loc'], params['radius'])
        elif params['type'] == 'triangle':
            self.draw_ngon(3, params['radius'], params['color'], params['loc'], params.get('start_angle', 30))
        elif params['type'] == 'square':
            self.draw_ngon(4, params['radius'], params['color'], params['loc'], params.get('start_angle', 45))
        elif params['type'] == 'hexagon':
            self.draw_ngon(6, params['radius'], params['color'], params['loc'], params.get('start_angle', 0))
        elif params['type'] == 'star':
            self.draw_star(params['points'], params['radius'], params['color'], params['loc'], params.get('start_angle', 270), params.get('inner_outer_ratio', 0.5))
        elif params['type'] == 'cross':
            self.draw_cross(params['radius'], params['color'], params['loc'], params.get('width', 1))
        elif params['type'] == 'image':
            img = params['image']
            img_rect = img.get_rect(center=params['loc'])
            self.screen.blit(img, img_rect)
        if self.debug_mode and 'window' in params:
            w, h = params['window']
            window = pygame.Rect(0, 0, w, h)
            window.center = params['loc']
            pygame.draw.rect(self.screen, pygame.Color('RED'), window, 4)

    def get_image_stimulus(self,path,**params):
        params['type'] = 'image'
        image = self.images.get(path)
        if image is None:
            self.images[path] = params['image'] = pygame.image.load(path).convert()
            if len(self.images) > self._image_cache_max_len:
                self.images.pop(list(self.images.keys())[0])
        else:
            params['image'] = image
        return params

    def get_item(self, item_key=None, **params):
        if item_key is not None:
            params.update(self.items[item_key])
        if params['type'] == 'image':
            params = self.get_image_stimulus(**params)
        return params

    def flip(self):
        self.screen.blit(self.info_screen,(0,0))
        pygame.display.update()

    def _start_trial(self, start_stimulus=None,duration=1e4):
        if start_stimulus is None:
            start_stimulus = dict(
                type='circle', 
                color=(100,100,255), 
                loc=(900,400),
                radius=100,
                window=(300,300)
            )

        self.screen.fill(self.background)
        self.draw_stimulus(**start_stimulus)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is not None:
                if self.was_tapped(start_stimulus['loc'], tap, start_stimulus['window']):
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    return info

    def update_info(self, trial):
        info = f"{self.params['monkey']} {self.params['task']} Trial#{trial}\n"
        for condition, condition_info in self.info.items():
            info += f"Condition {condition}: {condition_info[1]: 3d} correct, {condition_info[2]: 3d} incorrect\n"
        overall = sum(self.info.values(),Counter())
        info += f"Overall: {overall[1]: 3d} correct, {overall[2]: 3d} incorrect, {overall[0]: 3d} no response\n"

        self.info_screen.fill(self.info_background)
        for idx, line in enumerate(info.splitlines()):
            txt = self.font.render(line, True, pygame.Color('GREEN'))
            txt = pygame.transform.rotate(txt,90)
            self.info_screen.blit(txt, (idx*30,30))

        if self.data_dir is not None:
            self.info_screen.blit(self.session_txt, self.session_txt_rect)

        self.flip()

    def was_tapped(self, target, tap, window):
        """Check if tap was in a window around target location

        Parameters
        ----------
        target : list-like (2,)
            (x, y) coordinates for center of target location
        tap : list-like (2,)
            (x, y) coordinates of the tap
        window : list-like (2,)
            (width, height) of window centered at target

        Returns
        -------
        bool
            whether or not the tap was in the window
        """
        winx, winy = window
        return abs(tap[0] - target[0]) < (winx/2) \
            and abs(tap[1] - target[1]) < (winy/2)
