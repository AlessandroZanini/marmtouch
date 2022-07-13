import time
from pathlib import Path

import click

import marmtouch.util as util


@click.command()
@click.argument("task", required=True)
@click.argument("params_path", required=True)
@click.option(
    "--preview/--no-preview",
    default=False,
    help="Enables camera preview in info screen",
)
@click.option(
    "--camera/--no-camera",
    default=None,
    help="Enables recording with camera. Default, uses camera if available",
)
@click.option(
    "--debug/--no-debug", default=False, help="Enables debug mode.  Default, disabled"
)
@click.option(
    "--directory",
    default=None,
    help="Directory to save files. Default, uses system default directory (/home/pi/Touchscreen)",
)
@click.option(
    "--touch-exit/--no-touch-exit",
    default=True,
    help="Enables touching info screen to exit",
)
@click.option(
    '--fullscreen/--windowed',
    default=True,
    help='Enables fullscreen mode.  Default, enabled',
)
def run(task, params_path, preview, camera, debug, directory, touch_exit, fullscreen):
    if task == "basic":
        from marmtouch.experiments.basic import Basic as Task
    elif task == "memory":
        from marmtouch.experiments.memory import Memory as Task
    elif task == "dms":
        from marmtouch.experiments.dms import DMS as Task
    else:
        raise ValueError("Unknown task: {}".format(task))
    params = util.read_yaml(params_path)
    session = time.strftime("%Y-%m-%d_%H-%M-%S")
    if directory is None:
        data_dir = Path("/home/pi/Touchscreen", session)
    else:
        data_dir = Path(directory, session)
    experiment = Task(
        data_dir,
        params,
        camera_preview=preview,
        camera=camera,
        debug_mode=debug,
        touch_exit=touch_exit,
        fullscreen=fullscreen,
    )
    experiment.run_safe()
