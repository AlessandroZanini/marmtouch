import os

from picamera import PiCamera


def setup_screen():
    os.putenv("SDL_VIDEODRIVER", "fbcon")
    os.putenv("SDL_FBDEV", "/dev/fb1")
    os.putenv("SDL_MOUSEDRV", "TSLIB")
    os.putenv("SDL_MOUSEDEV", "/dev/input/touchscreen")


def setup_camera():
    camera = PiCamera()
    return camera
