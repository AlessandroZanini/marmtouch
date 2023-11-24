import os

import click

from marmtouch.scripts.util import get_task
from marmtouch.util import get_data_directory, read_yaml

@click.command()
@click.argument("task", required=True)
@click.argument("params_path", required=True)
@click.option(
    "--preview/--no-preview",
    default=False,
    help="Enables camera preview in info screen. Default, disabled.",
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
@click.pass_context
def run(ctx, task, params_path, preview, camera, debug, directory, touch_exit, fullscreen):
    """Uses marmtouch to run a task using the TASK experiment class and config at PARAMS_PATH."""
    Task = get_task(task)
    params = read_yaml(params_path)
    if directory is None:
        directory = get_data_directory()
    experiment = Task(
        directory,
        params,
        camera_preview=preview,
        camera=camera,
        debug_mode=debug,
        touch_exit=touch_exit,
        fullscreen=fullscreen,
        loglevel=ctx.obj["loglevel"],
    )
    experiment.run_safe()
