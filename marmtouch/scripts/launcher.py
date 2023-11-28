import math
import time
import tkinter as tk
from functools import partial
import os
from pathlib import Path

import click

import marmtouch.util as util
from marmtouch.scripts.transfer_files import bulk_transfer_files
from marmtouch.util.get_network_interfaces import get_network_interfaces

button_params = dict(
    height=3, width=20, relief=tk.FLAT, bg="gray99", fg="purple3", font="Dosis"
)

class PaginatedFrame(tk.Frame):
    """A pure Tkinter frame with pagination functionality.

    * Use the 'interior' attribute to place widgets inside the frame
    * Construct and pack/place/grid normally
    """

    def __init__(self, parent, page_size, *args, **kwargs):
        title = kwargs.pop("title", "Title")

        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.page_size = page_size
        self.current_page = 0
        self.child_widgets = []

        # Create a frame for the interior widgets
        self.title_label = tk.Label(self, 
            text=title,
            bg="purple3",
            fg="gray99",
            font="Helvetica 16 bold",
            height=3)
        self.title_label.pack(side=tk.TOP, fill=tk.X)

        self.interior = tk.Frame(self)
        self.buttons = tk.Frame(self)
        self.interior.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.TRUE)
        self.buttons.pack(side=tk.BOTTOM, fill=tk.X)

        self.prev_button = tk.Button(self.buttons, text="<<", command=self.prev_page, height=4)
        self.prev_button.pack(side=tk.LEFT, fill=tk.X, expand=tk.TRUE)
        self.next_button = tk.Button(self.buttons, text=">>", command=self.next_page, height=4)
        self.next_button.pack(side=tk.RIGHT, fill=tk.X, expand=tk.TRUE)
        self.page_label = tk.Label(self.buttons, text="Page 1/1", height=4)
        self.page_label.pack(side=tk.RIGHT, fill=tk.X, expand=tk.TRUE)

    @property    
    def num_pages(self):
        return math.ceil(len(self.child_widgets) / self.page_size)
    
    def draw(self):
        self.page_label.config(text=f"Page {self.current_page + 1}/{self.num_pages}")
        self.prev_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.NORMAL)
        if self.current_page == 0:
            self.prev_button.config(state=tk.DISABLED)
        if self.current_page == self.num_pages - 1:
            self.next_button.config(state=tk.DISABLED)
        
        for childid, child in enumerate(self.child_widgets):
            if childid // self.page_size == self.current_page:
                child.pack(padx=10, pady=5, side=tk.TOP)
            else:
                child.pack_forget()
    
    def prev_page(self):
        self.current_page -= 1
        self.draw()
    
    def next_page(self):
        self.current_page += 1
        self.draw()

    def add_widget(self, widget):
        self.child_widgets.append(widget)
    
    def reset(self):
        self.current_page = 0
        for child in self.child_widgets:
            child.destroy()
        self.child_widgets = []
        self.draw()
    
    def set_title(self, title):
        self.title_label.config(text=title)

class Launcher:
    def __init__(self, config_directory, debug=False):
        self.debug = debug
        self._init()
        self.config_directory = Path(config_directory)
        self.job_selector()
        self.root.mainloop()

    def _add_button(self, text, command):
        button = tk.Button(
            self.scframe.interior, text=text, command=command, **button_params
        )
        self.scframe.add_widget(button)

    def _init(self):
        self.root = tk.Tk()
        self.root.title("marmtouch launcher")
        
        system_config_path = os.environ.get(
            "MARMTOUCH_SYSTEM_CONFIG", self.default_system_config_path
        )
        system_config = util.read_yaml(system_config_path)
        launcher_settings = (system_config
            .get("screen_config", {})
            .get("launcher", {})
        )
        launcher_geometry = launcher_settings.get("geometry", "300x700+0+0")
        page_size = launcher_settings.get("page_size", 7)

        self.root.geometry(launcher_geometry)
        self.root.configure(background="gray99")
        self.scframe = PaginatedFrame(self.root, page_size, title="marmtouch launcher")
        self.scframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)

    def job_selector(self):
        self.scframe.reset()
        self.scframe.set_title("marmtouch launcher")
        jobs = [
            dict(text="Transfer Files", command=bulk_transfer_files),
            dict(text="Camera preview", command=self.preview_camera),
            dict(text="Test GPIO", command=self.test_GPIO_selector),
            dict(text="Tasks", command=self.task_selector),
            dict(text="Exit", command=self.exit),
        ]
        for job in jobs:
            self._add_button(**job)

        # display network interfaces and IP addresses on home display
        addresses = get_network_interfaces()
        addresses = "\n".join([f"{k}: {v}" for k, v in addresses.items()])
        addresses_label = tk.Label(self.scframe.interior, text=addresses, justify='left')
        self.scframe.add_widget(addresses_label)
        self.scframe.draw()

    def test_GPIO(self, port):
        from marmtouch.util import TTL

        TTL(port).pulse()

    def test_GPIO_selector(self):
        self.scframe.reset()
        self.scframe.set_title("TEST GPIO")
        jobs = [
            dict(text="reward", command=partial(self.test_GPIO, port=11)),
            dict(text="sync", command=partial(self.test_GPIO, port=16)),
            dict(text="<<", command=self.job_selector),
        ]
        for job in jobs:
            self._add_button(**job)
        self.scframe.draw()

    def preview_camera(self):
        from picamera import PiCamera

        camera = PiCamera()
        camera.start_preview()
        time.sleep(30)
        camera.stop_preview()

    def task_selector(self):
        self.scframe.reset()
        self.scframe.set_title("Select Task")
        task_list = [
            f
            for f in self.config_directory.iterdir()
            if f.is_dir() and not f.name.startswith(".")
        ]
        for task in task_list:
            self._add_button(
                text=task.name, command=partial(self.config_selector, task)
            )
        self._add_button(text="<<", command=self.job_selector)
        self.scframe.draw()

    def config_selector(self, task):
        self.scframe.reset()
        self.scframe.set_title(f"{task.name}: Select Config")
        config_list = list(task.glob("*.yaml"))
        for config in config_list:
            self._add_button(
                text=config.stem, command=partial(self.run, task=task, config=config)
            )
        self._add_button(text="<<", command=self.task_selector)
        self.scframe.draw()

    def run(self, task, config):
        params = util.read_yaml(config)
        data_dir = util.get_data_directory()
        if task.name in ["basic", "random", "reversal"]:
            from marmtouch.experiments.basic import Basic as Experiment
        elif task.name in ["memory", "cued", "vmcl", "auditory_discrimination"]:
            from marmtouch.experiments.memory import Memory as Experiment
        elif task.name in ["match", "nonmatch"]:
            from marmtouch.experiments.dms import DMS as Experiment
        else:
            raise ValueError(f"Task {task.name} not supported!")
        experiment = Experiment(data_dir, params, debug_mode=self.debug)
        experiment.run_safe()
        self.exit()

    def exit(self):
        self.root.destroy()


default_config_directory = "/home/pi/configs/"


@click.command()
@click.option('--debug/--no-debug', default=False, help='Run in debug mode, default is False')
def launch(debug):
    config_directory = os.environ.get("MARMTOUCH_CONFIG_DIRECTORY", default_config_directory)
    Launcher(config_directory, debug=debug)
