import os
import glob
import time
import datetime

import sys
import serial

import traceback

import spidev
import wiringpi2 as wiringpi
import RPi.GPIO as GPIO
from decimal import*
import signal

THREEPLACES = Decimal(10) ** -3
THREEPLACES=10**-3
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

SPICLK=11
SPIMISO=9
SPIMOSI=10
SPICS=8
#SENSOR1=22
#SENSOR2=27
#RELAY=17


GPIO.setup(SPIMOSI,GPIO.OUT)
GPIO.setup(SPIMISO,GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS,  GPIO.OUT)
#GPIO.setup(SENSOR1,  GPIO.OUT)
#GPIO.setup(SENSOR2,  GPIO.OUT)
#GPIO.setup(RELAY,  GPIO.OUT)


# function  to get data from specified pin of ADC
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
    if ((adcnum > 7) or (adcnum <0)):
        return -1

    GPIO.output(cspin,True)
    GPIO.output(clockpin,False)
    GPIO.output(cspin,False)

    commandout=adcnum
    commandout|=0x18
    commandout<<=3
    for i in range(5):
        if (commandout & 0x80):
            GPIO.output(mosipin,True)
        else:
            GPIO.output(mosipin,False)
        commandout<<=1
        GPIO.output(clockpin,True)
        GPIO.output(clockpin,False)

    adcout=0
    for i in range(14):
        GPIO.output(clockpin,True)
        GPIO.output(clockpin,False)
        adcout<<=1
        if(GPIO.input(misopin)):
            adcout|=0x1
    GPIO.output(cspin,True)

    adcout>>=1
    return adcout

def readchl(chlpin, chlslope, chlint):
    try:
        
        #Turn on chl probe using relay
        wiringpi.pinMode(chlpin, 1)
        wiringpi.digitalWrite(chlpin, 1)
        time.sleep(5)
        #read data from ADC chip
        #read data from ADC Chl 0
        ADC_Chl=0
        resp=readadc(ADC_Chl,SPICLK,SPIMOSI,SPIMISO,SPICS)
        # Format response from ADC chip
	ChlRaw = resp
        ChlVolts = (float(ChlRaw) / 4096) * 3.3
        ChlCal = (ChlVolts * chlslope) + chlint 
        print "ChlRaw is:", ChlRaw
        print"ChlVolts is:", ChlVolts
        print "ChlCal is:", ChlCal
        #turn off probe
        wiringpi.digitalWrite(chlpin, 0)
        return ChlRaw, ChlVolts, ChlCal
    except:
        print 'Read Chl Fail'
        ChlRaw = 'Fail'
        ChlVolts = 'Fail'
        ChlCal = 'Fail'
        wiringpi.digitalWrite(chlpin, 0)
        return ChlRaw, ChlVolts, ChlCal
	
def readcdom(cdompin, cdomslope, cdomint):
    try:
        #Turn on CDOM probe using relay 
        wiringpi.pinMode(cdompin, 1)
        wiringpi.digitalWrite(cdompin, 1)
        time.sleep(5)
        #read data from ADC chip    
        #read data from ADC Chl 1
        ADC_Chl=1
        resp=readadc(ADC_Chl,SPICLK,SPIMOSI,SPIMISO,SPICS)
        # Format response from ADC chip
        CDOMRaw = resp
        CDOMVolts = (float(CDOMRaw) / 4096) * 3.3
        CDOMCal = (CDOMVolts * cdomslope) + cdomint 
        print "CDOMRaw is:", CDOMRaw
        print"CDOMVolts is:", CDOMVolts
        print "CDOMCal is:", CDOMCal
        #turn off probe
        wiringpi.digitalWrite(cdompin, 0)
        return CDOMRaw, CDOMVolts, CDOMCal
    except:
        #print 'Read CDOM Fail'
        CDOMRaw = 'Fail'
        CDOMVolts = 'Fail'
        CDOMCal = 'Fail'
        wiringpi.digitalWrite(cdompin, 0)
        return CDOMRaw, CDOMVolts, CDOMCal
	
def readturb(turbID, turbslope, turbint):
    try:
#    for x in range(0,1):
    #Set up serial comms. Sensor connected by Prolific USB to Serial Converter 	
        port = serial.Serial("/dev/ttyUSB1", baudrate=1200, bytesize=7, parity='E', stopbits=1, xonxoff=0, rtscts=0, timeout=5)
        #Clear buffers
        port.flushInput()
        port.flushOutput()
        #Send command to initiate measurement
        port.write('single\r')
        time.sleep(1)
        #Read data
        response= port.readlines()
        #print(response)
        #Clear buffers and read again
        port.flushInput()
        port.flushOutput()
        #Send command to initiate measurement
        port.write('single\r')
        time.sleep(1)
        response= port.readlines()        
        #print(response)
        respvalues = []
        for t in response[3].split():
            try:
                respvalues.append(float(t))
            except ValueError:
                pass    
        TurbManu = respvalues[0]
        TurbRaw = respvalues[1]
        TurbCal = (TurbRaw*turbslope)+turbint
        print "TurbManu value is:", TurbManu
        print "TurbCal value is:", TurbCal
        print "TurbRaw is:", TurbRaw
        return TurbRaw, TurbCal, TurbManu
    except:
        print 'ReadTurbFail'
        TurbRaw = 'Fail'
        TurbCal = 'Fail'
        TurbManu = 'Fail'
        return TurbRaw, TurbCal, TurbManu
def readcond(condID, condslope, condint, tempslope, tempint):
    try:
    	#Set up serial comms. Sensor connected by Prolific USB to Serial Conveter 
    	port = serial.Serial("/dev/ttyUSB0", baudrate=4800, bytesize=8, parity='N', stopbits=1, xonxoff=0, rtscts=0, timeout=10)
    	
    	# wake up odyssey sensor
    	response = "No"
	trycount = 0
    	while response != "Hi!":
    		port.flushInput()
    		port.flushOutput()
    		port.write(chr(0x01))
    		response=port.read(3)
    		print(response)
		if trycount == 3 :
			break
		trycount = trycount + 1
    	
    	#Start trace mode by sending "T" followed by sensor ID
    	time.sleep(1)
    	port.flushOutput()
    	port.flushInput()
    	port.write(chr(0x54))
    	port.write(chr(0x1a))   

    	#Read data, data delivered in stream of 4 bytes representing 2 lots of 0-65535 values for temperature / salinity
    	data=port.read(4)
    	
    	#Test Code used to check calculations
    	#data1 =chr(int("0x09",16))
    	#data2 =chr(int("13",16))
    
    	#Calculate Temp & Conductivity
    	TempRaw = ord(data[0])+ord(data[1])*256
    	CondRaw = ord(data[2])+ord(data[3])*256
        # Perform Calibrations
        TempCal = (TempRaw*tempslope) + tempint
        CondCal = (CondRaw*condslope) + condint	
    	#End trace mode
    	response = "No"
    	while response !="Hi!":
    		port.flushInput()
    		port.flushOutput()
    		for count in range(0, 256):
    			port.write(chr(0x01))
    		response=port.read(3)
    	return TempRaw, CondRaw, TempCal, CondCal
    except:
        #print 'Read Temp/Cond Fail'
        TempRaw = 'Fail'
	CondRaw = 'Fail'
	TempCal = 'Fail'
	CondCal = 'Fail'
        return TempRaw, CondRaw, TempCal, CondCal
