# marmtouch

Experimental control for touchscreen experiments using a raspberry pi.  
  
Uses pygame to display stimuli and process inputs.  GPIO is used to trigger reward, send sync pulses, etc. PiCamera is used to handle recording of videos.  Click provides a commandline interface to easily use marmtouch tools
  
## Installation
```bash
sudo pip3 install git+https://github.com/jselvan/marmtouch.git
```

For developers:
```bash
git clone https://github.com/jselvan/marmtouch.git marmtouch
cd marmtouch
sudo pip3 install . -e
```

## Commandline Interface

The marmtouch commandline interface is installed when the python package is installed

The `-h` or `--help` flags can be used to get help text on available utilities

Available experiments can be launched via:
```bash
marmtouch run [experiment] [params_path]
```

The `marmtouch make-shortcut` utility can be used to make a desktop shortcut to easily launch on a touchscreen [under development]  
The `marmtouch transfer-files` utility can be used to transfer the files to a server or external storage device