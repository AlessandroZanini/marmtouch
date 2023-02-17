import random
import time
import warnings
from collections import ChainMap, Counter
from itertools import cycle
from pathlib import Path

import pygame
import RPi.GPIO as GPIO
import yaml

import marmtouch.util as util
from marmtouch import __version__
from marmtouch.experiments.mixins.artist import ArtistMixin
from marmtouch.experiments.mixins.events import EventsMixin
from marmtouch.experiments.util.pseudorandomize_conditions import \
    pseudorandomize_conditions
from marmtouch.experiments.util.generate_auditory_stimuli import \
    generate_sine_wave_snd
from marmtouch.util.svg2img import svg2img


class Experiment(ArtistMixin, EventsMixin):
    """Base Class for designing experiments in marmtouch

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
    TTLout: dict, default=None
        Dictionary of TTL output pins
        Must define 'reward' and 'sync' pins
        If None, will use default pins defined in Experiment.DEFAULT_TTL_OUT
    camera: bool, default=None
        If True, initialize camera and record videos
        If None, will be set to system_config['has_camera']
    camera_preview: bool, default=False
        If True, show camera preview window
        WARNING: This can overload the GPU and cause the system to crash
    camera_preview_window: tuple of int, default: (0,600,320,200)
        Window position and size for camera preview
    fullscreen: bool, default=True
        If True, run experiment in fullscreen mode
    debug_mode: bool, default=False
        If True, run experiment in debug mode
        In debug mode, some setup steps are skipped and the stimulus windows are displayed
    touch_exit: bool, default=True
        If True, exit experiment when touch is detected in the info screen
        Else, experiment can only be exited by escape key.
    system_config_path: Path or path-like, default=None
        Path to system configuration file
        If None, uses default path

    Notes
    -----
    [1] flip method must be called when screen is to be updated.
    Draw methods implemented in ArtistMixin do not do this automatically.
    """

    default_reward_params = dict(duration=0.2, n_pulses=1, interpulse_interval=1)
    keys = ["trial", "trial_start_time", "condition"]
    sep = ","
    info_background = (0, 0, 0)
    _image_cache_max_len = 20
    _audio_tracks_cache_max_len = 20
    system_config_path = "/home/pi/marmtouch_system_config.yaml"
    start_duration = 1e4
    start_stimulus = dict(
        type="circle",
        color=(100, 100, 255),
        loc=(900, 400),
        radius=100,
        window=(300, 300),
    )
    info_breakdown_keys = {
        "Condition": "condition",
    }
    outcome_key = "target_touch"
    
    DEFAULT_BLOCK_LENGTH = 100
    DEFAULT_TTL_OUT = {"reward": 11, "sync": 16}

    def __init__(
        self,
        data_dir,
        params,
        TTLout=None,
        camera=None,
        camera_preview=False,
        camera_preview_window=(0, 600, 320, 200),
        fullscreen=True,
        debug_mode=False,
        touch_exit=True,
        system_config_path=None,
    ):
        if system_config_path is None:
            system_config_path = self.system_config_path
        system_params = util.read_yaml(Path(system_config_path))
        params.update(system_params)
        self.debug_mode = debug_mode
        self.touch_exit = touch_exit

        data_dir = Path(data_dir)
        if not data_dir.is_dir():
            data_dir.mkdir()
        self.data_dir = data_dir
        self.behdata_path = self.data_dir / "behaviour.csv"
        self.logger_path = self.data_dir / "marmtouch.log"
        self.events_path = self.data_dir / "events.yaml"
        self.params_path = self.data_dir / "params.yaml"

        with open(self.params_path.as_posix(), "w") as f:
            yaml.dump(params, f)
        with open(self.behdata_path.as_posix(), "w") as f:
            f.write(",".join(self.keys) + "\n")

        self.logger = util.getLogger(self.logger_path.as_posix())

        # Initialize camera parameters
        self.camera_preview = camera_preview
        self.camera_preview_window = camera_preview_window
        if camera is None:
            camera = params.get("has_camera", True)
        if camera:
            self.camera = util.setup_camera()
        else:
            self.camera = None
        self.fullscreen = fullscreen

        # Set up TTL outputs
        if TTLout is None:
            TTLout = params.get("ttl", self.DEFAULT_TTL_OUT)
        self.TTLout = {k: util.TTL(v) for k, v in TTLout.items()}

        self.params = params
        self.timing = params["timing"]
        self.conditions = params["conditions"]
        self.background = params["background"]
        self.items = params["items"]
        self.reward = params.get("reward", self.default_reward_params)
        self.options = params.get("options", {})
        self.start_stimulus = self.options.get("start_stimulus", self.start_stimulus)
        self.start_duration = self.options.get("start_duration", self.start_duration)
        self.images = {}
        self.audio_tracks = {}

        self.trial = None
        blocks = params.get("blocks")
        self.max_blocks = self.options.get("n_blocks")
        self.block_number = 0
        if blocks is None:
            blocks = [
                {
                    "conditions": list(self.conditions.keys()),
                    "length": self.DEFAULT_BLOCK_LENGTH,
                }
            ]
        self.blocks = cycle(blocks)
        self.condition_list = []

        self.behdata = []
        self.events = []

        self.logger.info(f"experiment initialized using marmtouch version {__version__}")

    def good_monkey(self):
        """Rewards monkey 
        
        Pulses on `reward` pin as defined in `TTLout`
        Pulse parameters are defined in `config.reward`
        """
        self.TTLout["reward"].pulse(**self.reward)

    def get_duration(self, name):
        """Get NAME duration
        
        The duration may be defined in timing dictionary at the top level
        or in the timing dictionary of a specific block.

        Time may be defined as a float or list of floats.  If a list, a random
        value will be selected from the list.

        Parameters
        ----------
        name: str
            Name of duration to get
        
        Returns
        -------
        duration: float
            Duration in seconds

        Raises
        ------
        ValueError
            If duration is not defined
        """
        duration = ChainMap(self.active_block.get("timing", {}), self.timing).get(
            name, None
        )
        if duration is None:
            raise ValueError(f"{name} not in timing specification")
        if isinstance(duration, (int, float)):
            return duration
        else:
            return random.choice(duration)

    def graceful_exit(self):
        """Gracefully exit experiment
        
        Cleans up GPIO, stops and closes camera, saves behavioural and event data, and closes pygame window.
        """
        self.logger.info("graceful exit triggered")
        GPIO.cleanup()
        self.logger.info("GPIO cleaned up")
        if self.camera is not None:
            if self.camera.recording:
                self.camera.stop_recording()
            if self.camera_preview:
                self.camera.stop_preview()
            self.camera.close()
            self.logger.info("camera stopped and closed")

        self.dump_trialdata()
        self.logger.info("Behavioural data dumped.")
        with open(self.events_path.as_posix(), "w") as f:
            yaml.dump(self.events, f)
        self.logger.info(f"Event data dumped. {len(self.events)} total records.")
        self.running = False
        pygame.mixer.quit()
        pygame.quit()
        self.logger.info("Pygame quit safely.")

    def dump_trialdata(self):
        """Dump trial data to file
        
        If a trial is in progress, the available data is dumped.  Otherwise return

        Once dumped, trial data is appended to history and cleared.
        """
        if self.trial is None:
            return
        self.update_info_data()
        with open(self.behdata_path.as_posix(), "a") as f:
            f.write(self.trial.dump())
            f.write("\n")
        self.behdata.append(self.trial.data)
        self.trial = None

    def init_block(self, block_info):
        """Initialize block
        
        Use block info to set up condition list, randomization method and retry method

        Parameters
        ----------
        block_info: dict
            Dictionary containing block information.  Must contain `conditions` and `length` keys.
            Optionally defines `method`, `timing`, `retry_method`, `max_retries` and `weights`

            conditions: list
                List of condition names to use in block
            length: int
                Number of trials in block
            method: str, default "random"
                Method to use to select conditions.  Must be one of `random` or `incremental`
            timing: dict, default None
                Dictionary of timing parameters to use for this block
            retry_method: str, default None
                Method to use for retrying failed trials.  Must be one of `None`, `"immediate"` or `"delayed"`
            max_retries: int, default None
                Maximum number of retries to allow. If None, no limit is imposed.
            weights: list, default None
                list of weights for when randomizing conditions.  Must be same length as `conditions`
        
        Raises
        ------
        ValueError
            If `method` is not one of `random` or `incremental`
        """
        self.active_block = block_info
        method = block_info.get("method", "random")
        conditions = block_info["conditions"]
        length = block_info["length"]
        self.retry_method = block_info.get("retry_method")
        self.max_retries = block_info.get("max_retries")
        self.n_retries = Counter()
        if method == "random":
            weights = block_info.get("weights")
            max_reps = block_info.get("max_reps")
            self.condition_list = pseudorandomize_conditions(conditions, weights, length, max_reps)
        elif method == "incremental":
            condition_list = cycle(conditions)
            self.condition_list = [next(condition_list) for _ in range(length)]
        else:
            raise ValueError("'method' must be one of ['random','incremental']")

    def get_condition(self):
        """Get the condition for the next trial

        If the condition list is empty, get the next block and initialize it.

        Returns
        -------
        condition: 
            Condition name
        """
        if not self.condition_list:
            # check if we've reached the max number of blocks
            if self.max_blocks is not None and self.block_number >= self.max_blocks:
                self.graceful_exit()
                self.condition = None
                return
            # otherwise increment and get next block
            self.block_number += 1
            self.init_block(next(self.blocks))
        self.condition = self.condition_list.pop(0)
        return self.condition

    def update_condition_list(self, outcome, trialunique=False):
        """Update condition list

        If the trial was completed correctly, do nothing

        If the trial was completed incorrectly, determine how to update 
        condition list based on the retry_method.
        
        If retry_method is None or max_retries has been reached 
        for this condition, do nothing.

        If retry_method is "immediate", insert the current condition 
        back into the list at the first position.

        If retry_method is "delayed", insert the current condition
        back into the list at a random position.

        Parameters
        ----------
        correct: bool, default True
            Whether the trial was completed correctly
        trialunique: bool, default False
            Whether the experiment is set up to run in a trial unique manner
        
        Raises
        ------
        ValueError
            If `retry_method` is not one of `None`, `"immediate"` or `"delayed"`
        
        Warns
        -----
        UserWarning
            If using delayed retry method and `trialunique` is True
        """
        #always ignore correct trials
        if outcome == 1:
            return
        #if retry no response only, and no response, ignore
        if self.active_block.get("retry_noresponse_only", False) and outcome != 0:
            return

        retry_method = self.active_block.get("retry_method")
        max_retries = self.active_block.get("max_retries")
        if max_retries is not None:
            if self.n_retries[self.condition] >= max_retries:
                return
            self.n_retries[self.condition] += 1

        if retry_method is None:
            return
        elif retry_method == "delayed":
            idx = random.randint(0, len(self.condition_list))
            self.condition_list.insert(idx, self.condition)
            if trialunique:
                warnings.warn(
                    "Delayed retry does not repeat items in trial unique experiments"
                )
        elif retry_method == "immediate":
            self.condition_list.insert(0, self.condition)
            if trialunique:
                self.itemid -= 1
        else:
            raise ValueError(
                "'retry_method' must be one of [None,'delayed','immediate']"
            )

    def initialize(self):
        """Initialize experiment"""
        pygame.init()
        if not self.debug_mode:
            util.setup_screen()
            pygame.mouse.set_visible(1)
            pygame.mouse.set_cursor(
                (8, 8), (0, 0), (0, 0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0, 0)
            )
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((1200, 800))
        self.info = {}
        self.info_screen = pygame.Surface((350, 800))
        self.screen.fill(self.background)
        self.info_screen.fill(self.info_background)
        self.session_font = pygame.font.Font(None, 40)
        self.flip()

        if self.camera_preview:
            self.camera.start_preview(
                fullscreen=False, window=self.camera_preview_window
            )

        session_name = self.data_dir.name
        if self.debug_mode:
            session_name += " DEBUG MODE"
        text_colour = pygame.Color("RED") if self.debug_mode else pygame.Color("GREEN")
        session_txt = self.session_font.render(session_name, True, text_colour)
        self.session_txt = pygame.transform.rotate(session_txt, 90)
        self.session_txt_rect = self.session_txt.get_rect(bottomleft=(0, 800 - 30))
        pygame.mixer.init()

    def get_image_stimulus(self, path, **params):
        """Get image stimulus

        Parameters
        ----------
        path: str
            Path to image file
        params: dict
            Dictionary of parameters for the stimulus
        
        Returns
        -------
        params: dict
            Stimulus parameters with image data in `image` key
        """
        params["type"] = "image"
        image = self.images.get(path)
        if image is None:
            self.images[path] = params["image"] = pygame.image.load(
                path
            ).convert_alpha()
            if len(self.images) > self._image_cache_max_len:
                self.images.pop(list(self.images.keys())[0])
        else:
            params["image"] = image
        return params

    def get_svg_stimulus(self, path, **params):
        """Get SVG stimulus

        Load an svg and rasterize using optional colour and size parameters

        Parameters
        ----------
        path: str
            Path to SVG file
        params: dict
            Dictionary of parameters for the stimulus

        Returns
        -------
        params: dict
            Stimulus parameters with image data in `image` key
        """
        params["type"] = "svg"
        image = self.images.get(path)
        if image is None:
            self.images[path] = params["image"] = svg2img(
                path, colour=params["colour"], size=params["size"]
            )
            if len(self.images) > self._image_cache_max_len:
                self.images.pop(list(self.images.keys())[0])
        else:
            params["image"] = image
        return params
    
    def get_audio_stimulus(self, path, **params):
        """Get audio stimulus

        Load an audio file

        Parameters
        ----------
        path: str
            Path to audio file
        params: dict
            Dictionary of parameters for the stimulus

        Returns
        -------
        params: dict
            Stimulus parameters with audio data in `audio` key
        """
        params["type"] = "audio"
        audio = self.audio_tracks.get(path)
        if audio is None:
            self.audio_tracks[path] = params["sound"] = pygame.mixer.Sound(path)
            if len(self.audio_tracks) > self._audio_tracks_cache_max_len:
                self.audio_tracks.pop(list(self.audio_tracks.keys())[0])
        else:
            params["sound"] = audio
        return params

    def get_pure_tone_stimulus(self, **params):
        """Get pure tone stimulus

        Load parameters for a pure tone stimulus and generate it

        Parameters
        ----------
        
        """
        if "freq" not in params:
            raise ValueError("Must provide frequency for pure tone stimuli")
        params["maxtime"] = params.get("maxtime", 5)
        params["sound"] = generate_sine_wave_snd(params["freq"], params["maxtime"])
        return params

    
    def get_item(self, item_key=None, **params):
        """Get item parameters

        Get the item parameters using config file and parameters passed to the
        function. If the item is an image, load the image and add it to the
        image cache.  SVG files are rasterized using the colour and size
        parameters.

        Parameters
        ----------
        item_key: str, default None
            Item key
        params: dict
            Dictionary of parameters for the stimulus
        
        Returns
        -------
        params: dict
            Stimulus parameters
        """
        if item_key is not None:
            params.update(self.items[item_key])
            params["name"] = item_key
        if params["type"] == "image":
            params = self.get_image_stimulus(**params)
        elif params["type"] == "svg":
            params = self.get_svg_stimulus(**params)
        elif params["type"] == "audio":
            params = self.get_audio_stimulus(**params)
        elif params["type"] == "pure_tone":
            params = self.get_pure_tone_stimulus(**params)
        return params

    def flip(self):
        """Updates the screen"""
        self.screen.blit(self.info_screen, (0, 0))
        pygame.display.update()

    def _run_intertrial_interval(self, default_duration=5):
        """Run intertrial interval

        Parameters
        ----------
        default_duration: int, default 5
            Default duration of intertrial interval
        """

        start_time = time.time()
        while self.running and time.time() - start_time < self.options.get("iti", default_duration):
            self.parse_events()

    def _start_trial(self):
        """Run push to start trial
        
        A stimulus, as defined in :opt:`start_stimulus` is displayed and the
        subject must press it to start the trial within :opt:`start_duration`
        seconds.

        Returns
        -------
        info : dict or None
            Dictionary of information about the trial start, or None if the
            trial was aborted
        """
        self.screen.fill(self.background)
        self.draw_stimulus(**self.start_stimulus)
        self.flip()

        start_time = current_time = time.time()
        info = {"touch": 0, "RT": 0}
        while self.running and (current_time - start_time) < self.start_duration:
            current_time = time.time()
            tap = self.get_first_tap(self.parse_events())
            if tap is not None:
                if self.was_tapped(
                    self.start_stimulus["loc"], tap, self.start_stimulus["window"]
                ):
                    info = {
                        "touch": 1,
                        "RT": current_time - start_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    return info

    def update_info_data(self):
        key = tuple(self.trial.data[key] for key in self.info_breakdown_keys.values())
        if key not in self.info:
            self.info[key] = Counter()
        self.info[key][self.trial.data[self.outcome_key]] += 1

    def update_info(self, trial):
        """Update info screen

        Parameters
        ----------
        trial: int
            Trial number
        """
        overall = sum(self.info.values(), Counter())

        info_font_size = min(250//max(len(self.info), 1), 30)
        info_font = pygame.font.Font(None, info_font_size)

        info = f"{self.params['monkey']} {self.params['task']} Trial#{trial}\n"
        info += f"Overall: {overall[1]: 3d} correct, {overall[2]+overall.get(3,0): 3d} incorrect, {overall[0]: 3d} no response\n"
        for keys, trialcountdata in self.info.items():
            header = ", ".join([f"{field} {key}" for field, key in zip(self.info_breakdown_keys, keys)])
            trialcounts = f"{trialcountdata[1]: 3d} correct, {trialcountdata[2]+trialcountdata.get(3,0): 3d} incorrect"
            info += f"{header}: {trialcounts}\n"

        self.info_screen.fill(self.info_background)
        for idx, line in enumerate(info.splitlines()):
            txt = info_font.render(line, True, pygame.Color("GREEN"))
            txt = pygame.transform.rotate(txt, 90)
            self.info_screen.blit(txt, (idx * info_font_size, 30))

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

    def reached_max_responses(self):
        max_responses = self.options.get("max_responses")
        if max_responses is None:
            return False
        n_responses = sum(trial[self.outcome_key] != 0 for trial in self.behdata) 
        return n_responses >= max_responses
