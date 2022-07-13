from datetime import datetime

class Viewer:
    def __init__(self):
        self.ports = {}
    def add_port(self, port, initial=0):
        self.ports[port] = initial
    def set_port(self, port, value):
        self.ports[port] = value
        self.print()
    def print(self):
        now = datetime.now()
        print(f"{now:%H:%M:%S}.{int(now.microsecond//1e3):03d}", self.ports)

viewer = Viewer()