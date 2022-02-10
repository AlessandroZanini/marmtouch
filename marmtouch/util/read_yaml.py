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
    def range(self, node):
        rangestr = self.construct_yaml_str(node)
        start, stop = rangestr.split(':')
        if ':' in stop:
            step, stop = stop.split(':')
        else:
            step = '1'
        if any(not val.isdigit() for val in (start,step,stop)):
            raise ValueError('rangestr must be numbers separated by ":" in the format start:step:stop or start:stop')
        else:
            start, step, stop = int(start), int(step), int(stop)+1
        return list(range(start,stop,step))

Loader.add_constructor('!include', Loader.include)
Loader.add_constructor('!range', Loader.range)

def read_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.load(f, Loader)