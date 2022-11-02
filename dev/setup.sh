sudo apt install qemu-user-static
# run if needed https://github.com/eringr/pidock/blob/main/binfmt_setup.sh
# download img from: https://www.raspberrypi.com/software/operating-systems/
sudo losetup -Pf raspbian.img
sudo losetup -j raspbian.img

sudo mkdir /mnt/raspbian

LOOP=/dev/loop2p2
sudo mount $LOOP /mnt/raspbian
sudo tar -cjf root.tar -C /mnt .
sudo umount /mnt/raspbian

docker build -t marmtouch -f Dockerfile .
CONTAINER=$(docker run -d marmtouch bash)
docker export $CONTAINER > marmtouch.tar
docker container rm $CONTAINER

sudo mkfs.ext4 $LOOP