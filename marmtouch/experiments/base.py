import os
import random
import re
import sys
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
from marmtouch.experiments.mixins.block import BlockManagerMixin
from marmtouch.experiments.util.clock import Clock
from marmtouch.experiments.util.events import (
    EventHandler,
    get_first_tap,
    was_tapped,
)
from marmtouch.experiments.util.generate_auditory_stimuli import generate_sine_wave_snd
from marmtouch.experiments.util.parse_items import parse_item, parse_items
from marmtouch.util.svg2img import svg2img


class Experiment(ArtistMixin, BlockManagerMixin):
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
    default_system_config_path = "/home/pi/marmtouch_system_config.yaml"
    default_info_screen_spec = dict(
        size=(350, 800),
        loc=(0, 0),
    )
    default_screen_size = 1200, 800
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
        loglevel="WARN",
    ):
        if system_config_path is None:
            system_config_path = os.environ.get(
                "MARMTOUCH_SYSTEM_CONFIG", self.default_system_config_path
            )
        system_params = util.read_yaml(Path(system_config_path))
        params.update(system_params)
        self.debug_mode = debug_mode
        self.touch_exit = touch_exit

        # add stimulus directory to the path
        sys.path.append(
            params.get(
                "stimulus_directory",
                os.environ.get("MARMTOUCH_STIMULUS_DIRECTORY", "."),
            )
        )

        data_dir = Path(data_dir)
        if not data_dir.is_dir():
            data_dir.mkdir()
        self.data_dir = data_dir
        self.behdata_path = self.data_dir / "behaviour.csv"
        self.logger_path = self.data_dir / "marmtouch.log"
        self.events_path = self.data_dir / "events.yaml"
        self.temp_events_path = self.data_dir / "events.tmp.yaml"
        self.params_path = self.data_dir / "params.yaml"

        with open(self.params_path.as_posix(), "w") as f:
            yaml.dump(params, f)
        with open(self.behdata_path.as_posix(), "w") as f:
            f.write(",".join(self.keys) + "\n")

        self.logger = util.getLogger(self.logger_path.as_posix(), printLevel=loglevel)

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

        self.screen_config = params.get("screen_config", {})
        self.info_screen_spec = self.screen_config.get(
            "info_screen_spec", self.default_info_screen_spec
        )
        self.transform = self.screen_config.get("transform", None)
        self.screen_size = self.screen_config.get("size", self.default_screen_size)

        self.params = params
        self.timing = params["timing"]
        self.conditions = params["conditions"]
        self.background = params["background"]
        self.items = parse_items(params["items"], self.transform)
        self.reward = params.get("reward", self.default_reward_params)
        self.options = params.get("options", {})
        self.start_stimulus = parse_item(
            self.options.get("start_stimulus", self.start_stimulus), self.transform
        )
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
        self.block_list = blocks
        self.blocks = cycle(blocks)
        self.condition_list = []

        self.behdata = []
        self.events = []

        self.logger.info(
            f"experiment initialized using marmtouch version {__version__}"
        )

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
        return self._compute_duration(duration)

    def _compute_duration(self, duration):
        if isinstance(duration, (int, float)):
            return duration
        elif isinstance(duration, str):
            rand_template = r"rand\((?P<start>[\d.-]+),\s*(?P<end>[\d.-]+)\)"
            match = re.match(rand_template, duration)
            if match:
                start = float(match.group("start"))
                end = float(match.group("end"))
                return random.uniform(start, end)
            else:
                raise ValueError(f"Invalid duration string: {duration}")
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
        if self.events_path.stat().st_size == 0:
            warnings.warn("Event data did not save to disk. Keeping temp file.")
        else:
            self.logger.info("Event data saved properly.  Removing temp file.")
            if self.temp_events_path.exists():
                self.temp_events_path.unlink()
            else:
                warnings.warn("Temp file not found.")
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
            self.screen = pygame.display.set_mode(self.screen_size)
        self.info = {}
        self.info_screen = pygame.Surface(self.info_screen_spec["size"])
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

        self.clock = Clock()
        self.clock.start()
        self.event_manager = EventHandler(self, self.clock)

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
        self.info_screen_rect = self.screen.blit(
            self.info_screen, self.info_screen_spec["loc"]
        )
        pygame.display.update()

    def _run_intertrial_interval(self, default_duration=5):
        """Run intertrial interval

        Parameters
        ----------
        default_duration: int, default 5
            Default duration of intertrial interval
        """

        self.clock.wait(self.options.get("iti", default_duration))
        while self.running and self.clock.waiting():
            self.event_manager.parse_events()

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

        info = {"touch": 0, "RT": 0}
        self.clock.wait(self.start_duration)
        while self.running and self.clock.waiting():
            tap = get_first_tap(self.event_manager.parse_events())
            if tap is not None:
                if was_tapped(
                    self.start_stimulus["loc"], tap, self.start_stimulus["window"]
                ):
                    info = {
                        "touch": 1,
                        "RT": self.clock.elapsed_time,
                        "x": tap[0],
                        "y": tap[1],
                    }
                    break
        else:
            return None

        self.screen.fill(self.background)
        self.flip()

        info["start_stimulus_delay"] = self._compute_duration(
            self.options.get("start_stimulus_delay", 0)
        )

        self.clock.wait(info["start_stimulus_delay"])
        while self.running and self.clock.waiting():
            self.event_manager.parse_events()
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

        info_font_size = min(250 // max(len(self.info), 1), 30)
        info_font = pygame.font.Font(None, info_font_size)

        info = f"{self.params['monkey']} {self.params['task']} Trial#{trial}\n"
        info += f"Overall: {overall[1]: 3d} correct, {overall[2]+overall.get(3,0): 3d} incorrect, {overall[0]: 3d} no response\n"
        for keys, trialcountdata in self.info.items():
            header = ", ".join(
                [f"{field} {key}" for field, key in zip(self.info_breakdown_keys, keys)]
            )
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

    def initialize_test(self):
        # test initialisation
        pygame.init()
        self.screen = pygame.display.set_mode(self.screen_size)
        self.info = {}
        self.info_screen = pygame.Surface(self.info_screen_spec["size"])
        self.screen.fill(self.background)
        self.info_screen.fill(self.info_background)
        self.session_font = pygame.font.Font(None, 40)
        self.flip()
        session_name = self.data_dir.name + " DEBUG MODE"
        text_colour = pygame.Color("RED")
        session_txt = self.session_font.render(session_name, True, text_colour)
        self.session_txt = pygame.transform.rotate(session_txt, 90)
        self.session_txt_rect = self.session_txt.get_rect(bottomleft=(0, 800 - 30))
        self.debug_mode = True
        pygame.mixer.init()

    def capture_screen(self):
        return pygame.image.tobytes(self.screen, "RGB")

    def get_default_tests(self):
        raise NotImplementedError("Must implement get_default_tests method")

    def test(self, tests=None):
        from PIL import Image

        self.initialize_test()
        if tests is None:
            tests = self.get_default_tests()
        for test in tests:
            self._test_trial(test)
            imgdir = self.data_dir / str(test["trial"])
            imgdir.mkdir()
            for i, img in enumerate(self.captures):
                Image.frombytes("RGB", self.screen_size, img).save(imgdir / f"{i}.png")
        self.graceful_exit()

    def _setup_test_trial(self, test):
        self.running = True
        self.captures = []
        self.init_block(self.block_list[test["block"]])

        from marmtouch.experiments.util.clock import TestClock
        from marmtouch.experiments.util.events import TestEventHandler

        self.clock = TestClock()
        self.clock.start()
        self.event_manager = TestEventHandler(self, self.clock, test["event_queue"])
