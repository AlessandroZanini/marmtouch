import marmtouch.util as util
from marmtouch.experiments.mixins.artist import ArtistMixin
from marmtouch.experiments.mixins.events import EventsMixin

from pathlib import Path 
import time
import random
from itertools import cycle
from collections import Counter
import warnings

import RPi.GPIO as GPIO
import pygame
import yaml 

class Experiment(ArtistMixin, EventsMixin):
    """ Base Class for designing experiments in marmtouch

    Parameters
    ----------
    data_dir: Path or path-like, required
        Directory where all data is written to
        Includes: behaviour.csv, events.yaml, marmtouch.log and videos if camera=True
    params: dict, required
        All parameters for the experiment. 
        Must contain 'timing', 'items', 'conditions' and 'background' fields
        Optionally may include 'options', 'reward' to overwrite default settings
        May be further extended in subclasses
    TTLout: dict, required
    camera: bool, default=True
    camera_preview: bool, default=True
    camera_preview_window: tuple of int, default: (0,600,320,200)
    fullscreen: bool, default=True
    debug_mode: bool, default=False
    touch_exit: bool, default=True

    Notes
    -----
    [1] flip method must be called when screen is to be updated. 
    Draw methods implemented in ArtistMixin do not do this automatically.
    """
    default_reward_params = dict(duration=.2,n_pulses=1,interpulse_interval=1)
    keys = ['trial','trial_start_time','condition']
    sep = ','
    info_background = (0,0,0)
    _image_cache_max_len = 20
    system_config_path = '/home/pi/marmtouch_system_config.yaml'
    start_duration = 1e4
    start_stimulus = dict(
        type='circle', 
        color=(100,100,255), 
        loc=(900,400),
        radius=100,
        window=(300,300)
    )
    #TODO: move TTLout to system_config?
    #TODO: allow overwriting system_config_path from arg
    def __init__(self, data_dir, params, TTLout={'reward':11,'sync':16},
    camera=True, camera_preview=False, camera_preview_window=(0,600,320,200),
    fullscreen=True, debug_mode=False, touch_exit=True):
        system_params = util.read_yaml(Path(self.system_config_path))
        params.update(system_params)
        self.debug_mode = debug_mode
        self.touch_exit = touch_exit

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
        self.start_stimulus = self.options.get('start_stimulus', self.start_stimulus)
        self.start_duration = self.options.get('start_duration', self.start_duration)
        self.images = {}

        blocks = params.get('blocks')
        if blocks is None:
            blocks = [
                {'conditions': list(self.conditions.keys()), 
                'length': len(self.conditions)}
            ]
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
        self.dump_trialdata()
        self.logger.info('Behavioural data dumped.')
        with open(self.events_path.as_posix(), 'w') as f:
            yaml.dump(self.events, f)
        self.logger.info(
            f'Event data dumped. {len(self.events)} total records.'
        )
        self.running = False
        pygame.quit()

    def dump_trialdata(self,trialdata={}):
        #TODO: fix last trial off-by-one error with sync
        with open(self.behdata_path.as_posix(),'a') as f:
            f.write(self.sep.join([
                str(trialdata.get(key, 'nan')) 
                for key in self.keys
            ]))
            f.write('\n')
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
            self.camera.start_preview(
                fullscreen=False,
                window=self.camera_preview_window
            )

        session_name = self.data_dir.name
        if self.debug_mode:
            session_name += ' DEBUG MODE'
        text_colour = pygame.Color('RED') if self.debug_mode else pygame.Color('GREEN')
        session_txt = self.session_font.render(session_name, True, text_colour)
        self.session_txt = pygame.transform.rotate(session_txt,90)
        self.session_txt_rect = self.session_txt.get_rect(bottomleft=(0,800-30))

    def get_image_stimulus(self,path,**params):
        params['type'] = 'image'
        image = self.images.get(path)
        if image is None:
            self.images[path] = params['image'] = pygame.image.load(path).convert_alpha()
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

    def _start_trial(self):
        self.screen.fill(self.background)
        self.draw_stimulus(**self.start_stimulus)
        self.flip()

        start_time = current_time = time.time()
        info = {'touch':0,'RT':0}
        while (current_time-start_time) < self.start_duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if not self.running:
                return
            if tap is not None:
                if self.was_tapped(self.start_stimulus['loc'], tap, self.start_stimulus['window']):
                    info = {'touch':1, 'RT': current_time-start_time, 'x':tap[0], 'y':tap[1]}
                    return info

    def update_info(self, trial):
        info = f"{self.params['monkey']} {self.params['task']} Trial#{trial}\n"
        for condition, condition_info in self.info.items():
            info += f"Condition {condition}: {condition_info[1]: 3d} correct, {condition_info[2]+condition_info.get(3,0): 3d} incorrect\n"
        overall = sum(self.info.values(),Counter())
        info += f"Overall: {overall[1]: 3d} correct, {overall[2]+overall.get(3,0): 3d} incorrect, {overall[0]: 3d} no response"

        self.info_screen.fill(self.info_background)
        for idx, line in enumerate(info.splitlines()):
            txt = self.font.render(line, True, pygame.Color('GREEN'))
            txt = pygame.transform.rotate(txt,90)
            self.info_screen.blit(txt, (idx*30,30))

        self.info_screen.blit(self.session_txt, self.session_txt_rect)

        self.flip()

    def run_safe(self):
        """Runs experiment with graceful exit on errors

        Raises
        ------
        Exception
            Any unexpected error raised by Experiment.run is caught.
            Error is logged and the graceful_exit method is called
            Error is raised.
        """
        try:
            self.run()
        except Exception as err:
            self.logger.error(err)
            self.graceful_exit()
            raise err