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
        headerline = 'Time,Probe_TempRaw,Probe_TempCal,Condraw,CondCal,SpCond,Salinity,ChlRaw,ChlRawRangeCI,ChlVolts,ChlVoltsRangeCI,ChlCal,ChlCalRangeCI,CDOMRaw,CDOMVolts,CDOMCal,CDOMChlEQ,ChlAdj,TempRaw,TempCal'
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
    chlslope_1 = config.getfloat('Section1', 'chlslope_1')
    chlint_1 = config.getfloat('Section1', 'chlint_1')
    chlslope_10 = config.getfloat('Section1', 'chlslope_10')
    chlint_10 = config.getfloat('Section1', 'chlint_10')
    chlslope_100 = config.getfloat('Section1', 'chlslope_100')
    chlint_100 = config.getfloat('Section1', 'chlint_100')        
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

        # Chl gain switching, start at 10x move to 100x if reading is too low, move to 1x if reading is too high

        ChlRaw, ChlRaw_Range, ChlRaw_SEM, ChlVolts, ChlVolts_Range, ChlVolts_SEM, ChlCal, ChlCal_Range, ChlCal_SEM = readchl(chlpin, chladc, chlslope_10, chlint_10, 10)
        ChlGain = '10x'
        if(ChlVolts < 0.3):
            print('reading is less than 0.3V attempting 100X')
            ChlRaw, ChlRaw_Range, ChlRaw_SEM, ChlVolts, ChlVolts_Range, ChlVolts_SEM, ChlCal, ChlCal_Range, ChlCal_SEM = readchl(chlpin, chladc, chlslope_100, chlint_100, 100)
            ChlCal = ChlCal/10
            ChlCal_Range = ChlCal_Range/10
            ChlCal_SEM = ChlCal_SEM/10
            ChlGain = '100x'
        elif(ChlVolts > 4):
            print('reading is higher than 4V attempting 1X')
            ChlRaw, ChlRaw_Range, ChlRaw_SEM, ChlVolts, ChlVolts_Range, ChlVolts_SEM, ChlCal, ChlCal_Range, ChlCal_SEM = readchl(chlpin, chladc, chlslope_1, chlint_1, 1)
            ChlCal = ChlCal*10
            ChlCal_Range = ChlCal_Range*10
            ChlCal_SEM = ChlCal_SEM*10
            ChlGain = '1x'

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
        print('ChlGain', ChlGain)
        print('ChlRaw', ChlRaw, '+-', ChlRaw_Range)
        print('ChlVolts', ChlVolts, '+-', ChlVolts_Range)
        print('ChlCal', ChlCal, '+-', ChlCal_Range)
        print('CDOMRaw', CDOMRaw)
        print('CDOMVolts', CDOMVolts)
        print('CDOMCal', CDOMCal)
        print('CDOM Chl EQ', CDOMChlEQ)
        print('Chl Adjusted', ChlAdj)
        print('Tempraw', TempRaw)
        print('TempCal', TempCal)
        sys.stdout.flush()

        # Write results to file
        r = '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % (time.strftime("%d-%m-%Y %H:%M:%S"), Probe_TempRaw, Probe_TempCal, CondRaw, CondCal, SpCond, Salinity, ChlRaw, ChlRaw_Range, ChlVolts, ChlVolts_Range, ChlCal, ChlCal_Range, CDOMRaw, CDOMVolts, CDOMCal, CDOMChlEQ, ChlAdj, TempRaw, TempCal)
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
