from RPi.viewer import viewer
class PiCamera:
    def __init__(self):
        self.recording = False
        viewer.add_port('camera', 0)
    def start_recording(self, *args, **kwargs): 
        self.recording = True
        viewer.set_port('camera', 1)
    def stop_recording(self, *args, **kwargs): 
        self.recording = False
        viewer.set_port('camera', 0)