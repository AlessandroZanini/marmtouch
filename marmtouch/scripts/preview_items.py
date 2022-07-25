from marmtouch.util.read_yaml import read_yaml
from marmtouch.util.svg2img import svg2PIL

import click

@click.command()
@click.argument('CONFIG')
def preview_items(config):
    config = read_yaml(config)

    for item in config['items'].values():
        print(item)
        image = svg2PIL(item['path'], item['colour'], item['size'])
        image.show()