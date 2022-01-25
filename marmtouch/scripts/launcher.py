from marmtouch.scripts.transfer_files import bulk_transfer_files
import marmtouch.util as util

import tkinter as tk
from pathlib import Path
from functools import partial
import time

import click


button_params = dict(height=3, width=20, relief=tk.FLAT, bg="gray99", fg="purple3", font="Dosis")

class VerticalScrolledFrame(tk.Frame):
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    """
    def __init__(self, parent, *args, **kw):
        tk.Frame.__init__(self, parent, *args, **kw)            

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = tk.Scrollbar(self, orient=tk.VERTICAL)
        vscrollbar.pack(fill=tk.Y, side=tk.RIGHT, expand=tk.FALSE)
        canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = tk.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=tk.NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())

        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

class Launcher:
    def __init__(self,config_directory):
        self._init()
        self.config_directory = Path(config_directory)
        self.buttons = []
        self.job_selector()
        self.root.mainloop()
    
    def _recycle_buttons(self):
        for button in self.buttons:
            button.destroy()
        self.buttons = []
    
    def _add_button(self, text, command):
        button = tk.Button(self.scframe.interior, text=text, command=command, **button_params)
        button.pack(padx=10, pady=5, side=tk.TOP)
        self.buttons.append(button)

    def _init(self):
        self.root = tk.Tk()
        self.root.title("marmtouch launcher")
        self.root.geometry("300x700+0+0")
        self.root.configure(background="gray99")
        self.scframe = VerticalScrolledFrame(self.root)
        self.scframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
    
    def job_selector(self):
        self._recycle_buttons()
        jobs = [
            dict(text='Transfer', command=bulk_transfer_files),
            dict(text='Camera preview', command=self.preview_camera),
            dict(text='Test GPIO', command=self.test_GPIO_selector),
            dict(text='Tasks', command=self.task_selector),
            dict(text='Exit', command=self.exit)
        ]
        for job in jobs:
            self._add_button(**job)

    def test_GPIO(self, port):
        from marmtouch.util import TTL
        TTL(port).pulse()

    def test_GPIO_selector(self):
        self._recycle_buttons()
        jobs = [
            dict(text='reward', command=partial(self.test_GPIO, port=11)),
            dict(text='sync',command=partial(self.test_GPIO, port=16)),
            dict(text='<<',command=self.job_selector)
        ]
        for job in jobs:
            self._add_button(**job)

    def preview_camera(self):
        from picamera import PiCamera
        camera = PiCamera()
        camera.start_preview()
        time.sleep(30)
        camera.stop_preview()

    def task_selector(self):
        self._recycle_buttons()
        task_list = [f for f in self.config_directory.iterdir() if f.is_dir() and not f.name.startswith('.')]
        for task in task_list:
            self._add_button(text=task.name, command=partial(self.config_selector, task))
        self._add_button(text='<<', command=self.job_selector)

    def config_selector(self, task):
        self._recycle_buttons()
        config_list = list(task.glob('*.yaml'))
        for config in config_list:
            self._add_button(text=config.stem, command=partial(self.run, task=task, config=config))
        self._add_button(text='<<', command=self.task_selector)

    def run(self, task, config):
        params = util.read_yaml(config)
        session = time.strftime("%Y-%m-%d_%H-%M-%S")
        data_dir = Path('/home/pi/Touchscreen', session)
        if task.name in ['basic','random','reversal']:
            from marmtouch.experiments.basic import Basic
            experiment = Basic(data_dir, params)
        elif task.name in ['memory','cued']:
            from marmtouch.experiments.memory import Memory
            experiment = Memory(data_dir, params)
        elif task.name in ['match', 'nonmatch']:
            from marmtouch.experiments.dms import DMS
            experiment = DMS(data_dir, params)
        else:
            raise ValueError(f'Task {task.name} not supported!')
        try:
            experiment.run()
        except Exception as err:
            experiment.logger.error(err)
            experiment.graceful_exit()
            raise err
        self.exit()

    def exit(self):
        self.root.destroy()

default_config_directory = '/home/pi/configs/'
@click.command()
def launch():
    Launcher(default_config_directory)
