# AquaPi
Documentation for the Raspberry Pi based water quality monitoring system created by Daniel P. Harrison


## Pi first time setup
### Flash OS
#### Windows
Download Raspberry pi imager https://www.raspberrypi.com/software/
Raspberry Pi Device: Raspberry Pi 1
Operating System: Raspberry PI OS Lite (32-BIT)
OS Customisation settings: Services>Enable SSH, General>Set username/pw, General>Configure Wireless LAN: add SSID/pin, General>Set Locale settings>Time Zone: Sydney, Keyboard Layout: US
### RPi setup
sudo apt-get update
sudo apt-get upgrade
####Turn on 1-wire
https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/ds18b20
sudo raspi-config
Interfacing Options > 1-Wire > Yes
sudo reboot

sudo modprobe w1-gpio #add to /etc/rc.local (to apply at every boot)
sudo modprobe w1-therm #add to /etc/rc.local (to apply at every boot)

#### Install python and setup virtual environment
sudo apt-get install python3 python3-pip
python3 -m venv venv-aquapi
source venv-aquapi/bin/activate
cd aqua-pi
pip install -r requirements.txt
