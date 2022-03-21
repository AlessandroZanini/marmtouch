import time

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)


class TTL:
    def __init__(self, port, initial=0):
        GPIO.setup(port, GPIO.OUT, initial=initial)
        self.port = port

    def on(self):
        GPIO.output(self.port, True)

    def off(self):
        GPIO.output(self.port, False)

    def pulse(self, duration=0.2, n_pulses=1, interpulse_interval=1):
        for i in range(n_pulses):
            self.on()
            time.sleep(duration)
            self.off()
            if i + 1 < n_pulses:
                time.sleep(interpulse_interval)

    @property
    def value(self):
        return GPIO.input(self.port)
