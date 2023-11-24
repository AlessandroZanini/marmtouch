import time 

class Clock:
    def __init__(self):
        self.wait_start_time = None
        self.wait_for = None
        self.elapsed_time = None
    def start(self):
        self.start_time = time.time()
    def get_time(self):
        return time.time() - self.start_time
    def wait(self, t):
        self.wait_start_time = self.get_time()
        self.wait_for = t
    @property
    def wait_until(self):
        if self.wait_for is None:
            return None
        else:
            return self.wait_start_time + self.wait_for
    def waiting(self):
        if self.wait_for is None:
            return False
        else:
            self.elapsed_time = self.get_time() - self.wait_start_time
            return self.elapsed_time < self.wait_for
    def reset(self):
        self.wait_start_time = None
        self.wait_for = None
        self.elapsed_time = None

class TestClock(Clock):
    def __init__(self):
        super().__init__()
        self._time = 0
    def start(self, start=0):
        self.start_time = start
        self._time = start
    def advance_time(self, delta):
        self._time += delta
    def get_time(self):
        return self._time - self.start_time