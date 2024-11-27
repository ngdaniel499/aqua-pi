#!/usr/bin/python
#----------------------------------------------------------------------------------------------#
# NAME:         AquaPi.py
# CREATED:      August 10 2014
# CREATED BY:   Daniel P Harrison, University of Sydney 
#               Some intital code adapted from Bjorn Veltman & Adafruit
# Modification 1 By: Shariq Riaz, University of Sydney
#                       ADC read script is changed and pin numbers
# Modification 2 By: Daniel Harrison, conductivity cal changed to polynomial
# FUNCTION:     Operates the AquaPi Sensor Suite created by Daniel P Harrison as part of the Sydney
#               Harbour Research Program - Real Time Monitoring
# Modificaton 3 By: Shariq Riaz, University of Sydney
#                       Relay operation corrected, CAMPBELL temperature sensor interfaced
# run this script as: sudo python AquaPi.py config.cfg
# parameters values are given in Upconfig.cfg
# Modification 4 By: Daniel Ng, WhaleX
#                       Updated to python3, version control moved to github
#                       https://github.com/ngdaniel499/aqua-pi
#----------------------------------------------------------------------------------------------
import os
import glob
import time
import datetime
import configparser as ConfigParser
import sys
import serial
import traceback
import spidev
import wiringpi2 as wiringpi
import RPi.GPIO as GPIO
from decimal import*
import signal

from snsr import readadc, readchl, readtemp, readcdom, readcond

wiringpi.wiringPiSetupGpio()

def open_outputfile(fpath, stationid):
    outfile = stationid + '_' + time.strftime("%Y_%m_%d_%H")+'H.csv'
    fpathf = os.path.join(fpath, outfile)
    if os.path.exists(fpathf):
        f = open(fpathf, 'a')
    else:
        f = open(fpathf, 'w')
        headerline = 'Time,Probe_TempRaw,Probe_TempCal,Condraw,CondCal,SpCond,Salinity,ChlRaw,ChlVolts,ChlCal,CDOMRaw,CDOMVolts,CDOMCal,CDOMChlEQ,ChlAdj,TempRaw,TempCal'
        f.write(str(headerline))
        f.write('\n')
    return f, outfile, fpathf

# Start Main Program Here
try:
    config = ConfigParser.ConfigParser()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = 'Upconfig.cfg'
    configfilewithpath = os.path.join(current_dir, config_file)
    config.read(configfilewithpath)
    config_file = configfilewithpath.split('\\')[-1]
    base_dir = config.get('Section1', 'base_dir')
    slave_dir = config.get('Section1', 'slave_dir')
    fpath = os.path.join(current_dir, 'data/')
    stationid = config.get('Section1', 'stationid')
    readinterval = config.getfloat('Section1', 'readinterval')
    cdompin = config.getint('Section1', 'cdompin')
    chlpin = config.getint('Section1', 'chlpin')    
    temppin = config.getint('Section1', 'temppin')
    condpin = config.getint('Section1', 'condpin')
    cdomadc = config.getint('Section1', 'cdomadc')
    chladc = config.getint('Section1', 'chladc')
    tempadc = config.getint('Section1', 'tempadc')
    #Get calibration constants
    chlslope = config.getfloat('Section1', 'chlslope')
    chlint = config.getfloat('Section1', 'chlint')
    cdomslope = config.getfloat('Section1', 'cdomslope')
    cdomint = config.getfloat('Section1', 'cdomint')
    cdomchlslope = config.getfloat('Section1', 'cdomchlslope')
    cdomchlint = config.getfloat('Section1', 'cdomchlint')
    conda = config.getfloat('Section1', 'conda')
    condb = config.getfloat('Section1', 'condb')
    condc = config.getfloat('Section1', 'condc')
    condd = config.getfloat('Section1', 'condd')
    Probe_tempslope = config.getfloat('Section1', 'Probe_tempslope')
    Probe_tempint = config.getfloat('Section1', 'Probe_tempint')    
    tempslope = config.getfloat('Section1', 'tempslope')
    tempint = config.getfloat('Section1', 'tempint')
    #create output file
    f, outfile, fpathf = open_outputfile(fpath, stationid)
    #create variable for current file hour 
    now = datetime.datetime.now()
    checkhour = now.hour
    
    for x in range(0, 1):
        # Flush flow chamber
        wiringpi.wiringPiSetupGpio()
        
        # Conduct Measurements

        # Temperature / conductivity
        Probe_TempRaw, CondRaw, Probe_TempCal, CondCal, SpCond, Salinity = readcond(condpin, 'USB0', conda, condb, condc, condd, Probe_tempslope, Probe_tempint)

        # Chl
        ChlRaw_1, ChlVolts_1, ChlCal_1 = readchl(chlpin, chladc, chlslope, chlint, 1)
        ChlRaw_10, ChlVolts_10, ChlCal_10 = readchl(chlpin, chladc, chlslope, chlint, 10)
        ChlRaw_100, ChlVolts_100, ChlCal_100 = readchl(chlpin, chladc, chlslope, chlint, 100)
        time.sleep(0.5)
        
        # CDOM
        CDOMRaw, CDOMVolts, CDOMCal, CDOMChlEQ = readcdom(cdompin, cdomadc, cdomslope, cdomint, cdomchlslope, cdomchlint)
        ChlAdj = ChlCal - CDOMChlEQ

        # Temp
        TempRaw, TempVolts, TempCal = readtemp(temppin, tempadc, tempslope, tempint)
        
        #time.sleep(5)
        # For testing print results to screen
        print('Probe_Tempraw', Probe_TempRaw)
        print('Condraw', CondRaw)
        print('Probe_TempCal', Probe_TempCal)
        print('CondCal', CondCal)
        print('SpCond', SpCond)
        print('Salinity', Salinity)
        print('ChlRaw)', ChlRaw_1)
        print('ChlVolts', ChlVolts_1)
        print('ChlCal', ChlCal_1)
        print('ChlRaw)', ChlRaw_10)
        print('ChlVolts', ChlVolts_10)
        print('ChlCal', ChlCal_10)
        print('ChlRaw)', ChlRaw_100)
        print('ChlVolts', ChlVolts_100)
        print('ChlCal', ChlCal_100)
        print('CDOMRaw', CDOMRaw)
        print('CDOMVolts', CDOMVolts)
        print('CDOMCal', CDOMCal)
        print('CDOM Chl EQ', CDOMChlEQ)
        print('Chl Adjusted', ChlAdj)
        print('Tempraw', TempRaw)
        print('TempCal', TempCal)
        sys.stdout.flush()

        # Write results to file
        r = '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % (time.strftime("%d-%m-%Y %H:%M:%S"), Probe_TempRaw, Probe_TempCal, CondRaw, CondCal, SpCond, Salinity, ChlRaw, ChlVolts, ChlCal, CDOMRaw, CDOMVolts, CDOMCal, CDOMChlEQ, ChlAdj, TempRaw, TempCal)
        f.write(str(r))
        f.write('\n')
        f.close()

except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    error_msg = tbinfo + " " + str(sys.exc_info()[1])
    print(error_msg)
    f.write(error_msg)
    f.close()
