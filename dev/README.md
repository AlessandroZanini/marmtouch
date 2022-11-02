# marmtouch developer tools

Developer tools for marmtouch

## Development environment

To develop marmtouch code on non RPi devices, the GPIO and camera interfaces must be simulated.  Barebones simulations are available in `dev\simulated_packages` to achieve this.

Additionally, several paths on the RPi must be simulated for configs, stimuli, etc., to be loaded appropriately.

As in `dev\setup.ps1`, the simulated packages may be loaded by being added to the `PYTHONPATH` environment variable, and the file structure can be simulated via symlinks.

## Schema
Schemas allow 