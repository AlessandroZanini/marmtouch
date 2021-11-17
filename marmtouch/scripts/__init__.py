from marmtouch.scripts.make_shortcut import make_shortcut
from marmtouch.scripts.run import run
from marmtouch.scripts.transfer_files import transfer_files
from marmtouch.scripts.launcher import launch

import click

@click.group()
def marmtouch():
    pass

marmtouch.add_command(run)
marmtouch.add_command(make_shortcut)
marmtouch.add_command(transfer_files)
marmtouch.add_command(launch)

if __name__ == '__main__':
    marmtouch()