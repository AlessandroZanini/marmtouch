# marmtouch developer tools

Developer tools for marmtouch

## Development environment

To develop marmtouch code on non RPi devices, the GPIO and camera interfaces must be simulated.  Barebones simulations are available in `dev\simulated_packages` to achieve this.

Additionally, several paths on the RPi must be set up for files to be referenced properly.  

To achieve this, we can set up a venv with the required packages (see `requirements.txt`), and copy in the simulated packages.  Then, the environment variables for the required directories can be set and the marmtouch CLI command can be exported.

Example scripts to do this are provided for windows `dev.ps1` and unix `dev.sh` devices.

## Schema

Schemas are still under development, and provide some metadata guiding config creation