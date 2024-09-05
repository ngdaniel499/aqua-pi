#!/usr/bin/python
#----------------------------------------------------------------------------------------------#
# NAME:         AquaPi.py
# CREATED:      August 10 2014
# CREATED BY:   Daniel P Harrison, University of Sydney 
# 	        	Some intital code adapted from Bjorn Veltman & Adafruit
# Modification 1 By: Shariq Riaz, University of Sydney
#                       ADC read script is changed and pin numbers
# Modification 2 By: Daniel Harrison, conductivity cal changed to polynomial
# FUNCTION:     Operates the AquaPi Sensor Suite created by Daniel P Harrison as part of the Sydney
#               Harbour Research Program - Real Time Monitoring
#
# run this script as: sudo python AquaPi.py config.cfg
# parameters values are given in Upconfig.cfg
#----------------------------------------------------------------------------------------------
import os
import glob
import time
import datetime
import ConfigParser
import sys
import serial
#from ftplib import FTP
import traceback
#from ftpupallAuto import ftpupload
import spidev
import wiringpi2 as wiringpi
import RPi.GPIO as GPIO
from decimal import*
import signal

from SNSR import readadc,readchl,readcdom,readturb,readcond

wiringpi.wiringPiSetupGpio()

"""THREEPLACES = Decimal(10) ** -3
THREEPLACES=10**-3
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

SPICLK=11
SPIMISO=9
SPIMOSI=10
SPICS=8
SENSOR1=22
SENSOR2=27
RELAY=17

GPIO.setup(SPIMOSI,GPIO.OUT)
GPIO.setup(SPIMISO,GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS,  GPIO.OUT)
GPIO.setup(SENSOR1,  GPIO.OUT)
GPIO.setup(SENSOR2,  GPIO.OUT)
GPIO.setup(RELAY,  GPIO.OUT)
"""

        
def open_outputfile(fpath, stationid):
    outfile = 'calibrate_' + stationid + '_' + time.strftime("%Y_%m_%d_%H")+'H.csv'
    fpathf = os.path.join(fpath,outfile)
    if os.path.exists(fpathf):
        f = open(fpathf,'a')
    else:
        f = open(fpathf,'w')
        headerline = 'Time,Tempraw,TempCal,Condraw,CondCal,SpCond,Salinity,Turbraw,TurbCal,TurbManu,ChlRaw,ChlVolts,ChlCal,CDOMRaw,CDOMVolts,CDOMCal,CDOMChlEQ, ChlAdj'
        f.write(str(headerline))
        f.write('\n')
    return f, outfile, fpathf

# Start Main Program Here
try:
    config = ConfigParser.ConfigParser()
    configfilewithpath =  '/home/pi/PythonScripts/FINAL_CODE/Upconfig.cfg'
    config.read(configfilewithpath)
    config_file = configfilewithpath.split('\\')[-1]
    base_dir = config.get('Section1', 'base_dir')
    slave_dir = config.get('Section1', 'slave_dir')
    fpath = config.get('Section1', 'fpath')
    stationid = config.get('Section1', 'stationid')
    readinterval = config.getfloat('Section1', 'readinterval')
    cdompin = config.getint('Section1', 'cdompin')
    chlpin = config.getint('Section1', 'chlpin')    
    pumppin = config.getint('Section1', 'pumppin')
    pumpflush = config.getint('Section1', 'pumpflush')
    server_ip = config.get('Section1', 'server_ip')
    username = config.get('Section1', 'username')
    password = config.get('Section1', 'password')
    ftp_dir = config.get('Section1', 'ftp_dir')
    #Get calibration constants
    chlslope = config.getfloat('Section1', 'chlslope')
    chlint = config.getfloat('Section1', 'chlint')
    cdomslope = config.getfloat('Section1', 'cdomslope')
    cdomint = config.getfloat('Section1', 'cdomint')
    cdomchlslope = config.getfloat('Section1', 'cdomchlslope')
    cdomchlint = config.getfloat('Section1', 'cdomchlint')
    turbslope = config.getfloat('Section1', 'turbslope')
    turbint = config.getfloat('Section1', 'turbint')
    conda = config.getfloat('Section1', 'conda')
    condb = config.getfloat('Section1', 'condb')
    condc = config.getfloat('Section1', 'condc')
    condd = config.getfloat('Section1', 'condd')
    tempslope = config.getfloat('Section1', 'tempslope')
    tempint = config.getfloat('Section1', 'tempint')    
    #create output file
    f, outfile, fpathf = open_outputfile(fpath, stationid)
    #create variable for current file hour 
    now = datetime.datetime.now()
    checkhour = now.hour
  
    # Flush flow chamber
    wiringpi.wiringPiSetupGpio()
    wiringpi.pinMode(pumppin, 1)
    wiringpi.digitalWrite(pumppin, 1)
    time.sleep(30)
        
    for x in range (0,5):
    #    for x in range(0, 10):

        # Conduct Measurements

        # Temperature / conductivity
        TempRaw, CondRaw, TempCal, CondCal, SpCond, Salinity = readcond('USB0',conda,condb,condc, condd, tempslope, tempint)

	# Turbidity
        TurbRaw, TurbCal, TurbManu = readturb('USB1', turbslope, turbint)
	
        #Chl
        ChlRaw, ChlVolts, ChlCal = readchl(chlpin, chlslope, chlint)
        
        #CDOM
        CDOMRaw, CDOMVolts, CDOMCal, CDOMChlEQ = readcdom(cdompin, cdomslope, cdomint, cdomchlslope, cdomchlint)
        ChlAdj = ChlCal - CDOMChlEQ
        

        #time.sleep(5)
        # For testing print results to screen
        print('Tempraw',TempRaw)
        print('Condraw',CondRaw)
        print('TempCal',TempCal)
        print('CondCal',CondCal)
        print('SpCond',SpCond)
        print('Salinity',Salinity)
        print('Turbraw',TurbRaw)
        print('Turbcal',TurbCal)
        print('ChlRaw)',ChlRaw)
        print('ChlVolts',ChlVolts)
        print('ChlCal',ChlCal)
        print('CDOMRaw',CDOMRaw)
        print('CDOMVolts',CDOMVolts)
        print('CDOMCal',CDOMCal)
        print('CDOM Chl EQ',CDOMChlEQ)
        print('Chl Adjusted',ChlAdj)
	sys.stdout.flush()

        # Write results to file
        r = '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % (time.strftime("%d-%m-%Y %H:%M:%S"), TempRaw, TempCal, CondRaw, CondCal, SpCond, Salinity, TurbRaw, TurbCal, TurbManu, ChlRaw, ChlVolts, ChlCal, CDOMRaw, CDOMVolts, CDOMCal, CDOMChlEQ, ChlAdj)
        f.write(str(r))
        f.write('\n')
	f.close
    
    # Stop Pump       
    wiringpi.digitalWrite(pumppin, 0)

except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    error_msg = tbinfo + " " + str(sys.exc_info()[1])
    print error_msg
    f.write(error_msg)
    f.close()
