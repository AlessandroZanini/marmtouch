import marmtouch.util as util

import time
from pathlib import Path

import click

@click.command()
@click.argument('task', required=True)
@click.argument('params_path', required=True)
@click.option('--preview/--no-preview',default=False,help='Enables camera preview in info screen')
@click.option('--camera/--no-camera',default=True,help='Enables recording with camera')
@click.option('--debug/--no-debug',default=False,help='Enables debug mode')
@click.option('--directory', default=None, help='Directory to save files')
def run(task,params_path,preview,camera,debug,directory):
    if task=='basic':
        from marmtouch.experiments.basic import Basic as Task
    elif task=='memory':
        from marmtouch.experiments.memory import Memory as Task
    elif task=='dms':
        from marmtouch.experiments.dms import DMS as Task
    else:
        raise ValueError('Unknown task: {}'.format(task))
    params = util.read_yaml(params_path)
    session = time.strftime("%Y-%m-%d_%H-%M-%S")
    if directory is None:
        data_dir = Path('/home/pi/Touchscreen', session)
    else:
        data_dir = Path(directory, session)
    experiment = Task(data_dir, params, camera_preview=preview, camera=camera, debug_mode=debug)
    try:
        experiment.run()
    except Exception as err:
        experiment.logger.error(err)
        experiment.graceful_exit()
        raise err