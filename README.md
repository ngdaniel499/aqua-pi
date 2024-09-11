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
	sudo apt-get update

	sudo apt-get upgrade

#### Turn on 1-wire

Refernce: https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/ds18b20

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
#### Setup Crontab with debugging log
	crontab -e #add the line below to the bottom of crontab and save
 	*/15 * * * * (date && echo "Starting job" && cd ~/ && echo "Changed directory" && . venv-aquapi/bin/activate && echo "Activated venv" && python aqua-pi/python-scripts/main.py && echo "Ran Python script") >> /tmp/cronrun.log 2>&1
