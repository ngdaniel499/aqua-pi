# AquaPi
Documentation for the Raspberry Pi based water quality monitoring system created by Daniel P. Harrison


## Pi first time setup
### Flash OS
#### Windows
Download Raspberry pi imager https://www.raspberrypi.com/software/

Raspberry Pi Device: Raspberry Pi 1

Operating System: Raspberry PI OS Lite (32-BIT)
	
 	PRETTY_NAME="Raspbian GNU/Linux 12 (bookworm)"
	NAME="Raspbian GNU/Linux"
	VERSION_ID="12"
	VERSION="12 (bookworm)"
	VERSION_CODENAME=bookworm
	ID=raspbian
	ID_LIKE=debian
	HOME_URL="http://www.raspbian.org/"
	SUPPORT_URL="http://www.raspbian.org/RaspbianForums"
	BUG_REPORT_URL="http://www.raspbian.org/RaspbianBugs"
	 
OS Customisation settings: 

	Services>Enable SSH, 

	General>Set username/pw, 

	General>Configure Wireless LAN: add SSID/pin, 

	General>Set Locale settings>Time Zone: Sydney, 

	General>Set Locale settings>Keyboard Layout: US

### RPi setup
	sudo ip link set eth1 down
 
  	sudo ip link set usb0 down
  
	sudo apt-get update

	sudo apt-get upgrade

#### configure startup for 1-wire and wlan0
	sudo nano /etc/rc.local

	#add the following lines above exit 0
     
	sudo modprobe w1-gpio
	
	sudo modprobe w1-therm

 	sudo nano /etc/network/interfaces
  	#add the following lines 
   	auto wlan0
	iface wlan0 inet dhcp
    		metric 1

#### Turn on 1-wire

Refernce: https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/ds18b20

	sudo raspi-config

		Interfacing Options > 1-Wire > Yes

	sudo reboot



#### Install aqua-pi files and dependencies and setup virtual environment
	sudo apt install git
 
  	cd ~
  
 	git clone https://github.com/ngdaniel499/aqua-pi.git
 
	cd ~/aqua-pi

	sudo apt-get install python3 python3-pip

	python3 -m venv .venv

	source .venv/bin/activate

	pip install -r requirements.txt
#### Setup Crontab with debugging log
	# Run AquaPi measurement (main) job every 15 minutes
	*/15 * * * * /home/pi/aqua-pi/python-scripts/cron-main.sh
	
	# Run Pump script every 15 minutes with a 7 minute offset
	7-59/15 * * * * /home/pi/aqua-pi/python-scripts/cron-pump.sh
 
