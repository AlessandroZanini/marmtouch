import math

import pygame

def generate_sine_wave_snd(freq, maxtime=5, sample_rate=44100):
    """Generate a pure tone sine wave

    Parameters
    ----------
    freq: int
        Frequency of tone in Hz
    maxtime: float
        Duration of sound in seconds
    sample_rate: int, default 44100Hz
        Sampling rate of sound
    
    Returns
    -------
    snd: pygame.sndarray objects
    """
    snd = [4096 * math.sin(2. * math.pi * freq * x / sample_rate) for x in range(sample_rate*maxtime)]
    snd = [snd, snd]
    snd = pygame.sndarray.make_sound(snd)
    return snd