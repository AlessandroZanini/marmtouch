import click

from marmtouch import __version__
from marmtouch.scripts.launcher import launch
from marmtouch.scripts.make_shortcut import make_shortcut
from marmtouch.scripts.preview_items import preview_items
from marmtouch.scripts.run import run
from marmtouch.scripts.transfer_files import transfer_files


@click.group()
@click.version_option(version=__version__)
def marmtouch():
    print(f"marmtouch version {__version__}")


marmtouch.add_command(run)
marmtouch.add_command(make_shortcut)
marmtouch.add_command(transfer_files)
marmtouch.add_command(launch)
marmtouch.add_command(preview_items)

if __name__ == "__main__":
    marmtouch()
