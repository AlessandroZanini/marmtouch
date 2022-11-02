FROM scratch

USER root
ADD root.tar /
RUN apt-get update
RUN apt-get install network-manager network-manager-gnome vim cifs-utils python3 python3-pip -y
RUN systemctl disable --now dhcpcd
RUN pip3 install git+file:///mnt/Data/Touchscreen/marmtouch -U
RUN raspi-config nonint do_vnc 1
RUN raspi-config nonint do_ssh 1
RUN raspi-config nonint do_resolution 1280 800
RUN echo "pi:marmoset" | chpasswd