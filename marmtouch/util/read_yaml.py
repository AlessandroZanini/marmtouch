import yaml
from pathlib import Path
import os

class Loader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = Path(stream.name).parent
        super(Loader, self).__init__(stream)

    def include(self, node):
        filename = self.construct_scalar(node)
        if Path(filename).is_file():
            filename = Path(filename)
        elif (self._root/filename).is_file():
            filename = self._root/filename
        else:
            raise FileNotFoundError('Could not find file: {}. Must be absolute path or relative to yaml.'.format(filename))
        with open(filename, 'r') as f:
            return yaml.load(f, Loader)
    

Loader.add_constructor('!include', Loader.include)

def read_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.load(f, Loader)