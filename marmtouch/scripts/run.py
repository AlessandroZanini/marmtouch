import time
from pathlib import Path

import click
import yaml

@click.group()
def run():
    pass

@click.command()
@click.argument('params_path', required=True)
@click.option('--preview/--no-preview',default=False,help='Enables camera preview in info screen')
def memory(params_path,preview):
    """ Run memory paradigm using parameters specified at PARAMS_PATH """
    from marmtouch.experiments.memory import Memory #import here so that script utility isn't slowed down

    params = yaml.safe_load(open(params_path))
    session = time.strftime("%Y-%m-%d_%H-%M-%S")
    data_dir = Path('/home/pi/Touchscreen', session)
    memory = Memory(data_dir, params,camera_preview=preview)
    #TODO: implement lock to prevent double running?
    memory.run()

run.add_command(memory)