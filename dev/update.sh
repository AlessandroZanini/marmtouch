sudo mount -a
sudo pip3 install git+file:///mnt/Data/Touchscreen/marmtouch -U
rsync --exclude=.DS_Store -ai /mnt/Data/Touchscreen/configs/ /home/pi/configs
rsync --exclude=.DS_Store --exclude=Thumbs.db -aui /mnt/Data/Touchscreen/stimuli/ /home/pi/stimuli
