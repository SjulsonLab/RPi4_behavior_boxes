add  "dtparam=i2c_vc=on"  to   /boot/config.txt

enable iic in raspi-config

reboot 

test if i2c is enabled by typing "sudo i2cdetect -y 1"
  This shows you the connected device
If an error appears - "i2cdetect command not found"

sudo apt-get update
sudo apt-get install i2c-tools

reboot

run the code
