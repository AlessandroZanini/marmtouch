from pathlib import Path

import click

template = """[Desktop Entry]
Type=Application
Encoding=UTF-8
NAME=touch
Exec={command}
Icon={icon}
StartupNotify=true
Terminal=true
Name[en_GB]={name}
"""

@click.command()
@click.argument('command',required=True)
@click.argument('name',required=True)
@click.option('--fname',default=None,help='Name of the file, defaults to ~/Desktop/NAME')
@click.option('--icon',default='/home/pi/Pictures/basic.jpg',help='Path to icon file, defaults to /home/pi/Pictures/basic.jpg')
def make_shortcut(command, name, fname, icon):
    """ Make shortcut at NAME to execute COMMAND """
    shortcut_info = template.format(command=command, icon=icon, name=name)
    if fname is None:
        fname = Path('~/Desktop', name)
    with open(fname, 'w') as f:
        f.write(shortcut_info)