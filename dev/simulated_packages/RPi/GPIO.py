from RPi.viewer import viewer

def input(*args,**kwargs):
    pass
def output(port, value):
    viewer.set_port(port, int(value))
def setup(port, state, initial=0):
    viewer.add_port(port, initial)
def cleanup(*args,**kwargs):
    pass
def setmode(*args,**kwargs):
    pass
def setwarnings(*args,**kwargs):
    pass
OUT = None
BOARD = None