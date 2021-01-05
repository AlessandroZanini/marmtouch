from .make_shortcut import make_shortcut
from .run import run
from .transfer_files import transfer_files

import click

@click.group()
def marmtouch():
    pass

marmtouch.add_command(run)
marmtouch.add_command(make_shortcut)
marmtouch.add_command(transfer_files)