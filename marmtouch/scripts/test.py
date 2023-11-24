import click

from marmtouch.scripts.util import get_task
from marmtouch.util import get_data_directory, read_yaml

@click.command()
@click.argument("task")
@click.argument("params_path")
@click.argument("test_path")
@click.option(
    "--directory",
    default=None,
    help="Directory to save files. Default, uses system default directory (/home/pi/Touchscreen)",
)
@click.pass_context
def test(ctx, task, params_path, test_path, directory):
    Task = get_task(task)
    params = read_yaml(params_path)
    if directory is None:
        directory = get_data_directory()
    experiment = Task(
        directory,
        params,
        loglevel=ctx.obj["loglevel"],
    )
    experiment.test(read_yaml(test_path))
