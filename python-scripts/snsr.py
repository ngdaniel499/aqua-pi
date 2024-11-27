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



GPIO.setup(SPIMOSI,GPIO.OUT)
GPIO.setup(SPIMISO,GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS,  GPIO.OUT)


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

def readchl(chlpin, chladc,chlslope, chlint, gain):
    try:
        print(gain)
        if gain not in {1, 10, 100}:
            print(f"Invalid gain value '{gain}'. Must be '1', '10', or '100'. Exiting.")
            sys.exit(1)

        TENX_PIN = 22
        HUNDREDX_PIN = 27
        #Turn on chl probe using relay
        wiringpi.pinMode(chlpin, 1)
        wiringpi.digitalWrite(chlpin, 0)
        if gain == 1:
            print("Chla gain: 1x")
            wiringpi.digitalWrite(TENX_PIN, 0)
            wiringpi.digitalWrite(HUNDREDX_PIN, 0)
        elif gain == 10:
            print("Chla gain: 10x")
            wiringpi.digitalWrite(TENX_PIN, 1)
            wiringpi.digitalWrite(HUNDREDX_PIN, 0)
        elif gain == 100:
            print("Chla gain: 100x")
            wiringpi.digitalWrite(TENX_PIN, 0)
            wiringpi.digitalWrite(HUNDREDX_PIN, 1)
             
        time.sleep(5)
        #read data from ADC chip
        #read data from ADC Chl 0
        ADC_Chl=chladc
        resp_moving_average = 0
        n_resp = 0
        t_sleep = 0.03
        start_time = time.time()
        while time.time() - start_time < 3:
            n_resp += 1
            resp_moving_average = readadc(ADC_Chl,SPICLK,SPIMOSI,SPIMISO,SPICS)
            time.sleep(t_sleep)
        resp= resp_moving_average/n_resp
        # Format response from ADC chip
        ChlRaw = resp
        ChlVolts = (float(ChlRaw) / 4095) * 5
        ChlCal = (ChlRaw * chlslope) + chlint 
        
        print("ChlRaw is:", ChlRaw)
        print("ChlVolts is:", ChlVolts)
        print("ChlCal is:", ChlCal)
        #turn off probe
        wiringpi.digitalWrite(chlpin, 1)
        return ChlRaw, ChlVolts, ChlCal
    except:
        print('Read Chl Fail')
        ChlRaw = 'Fail'
        ChlVolts = 'Fail'
        ChlCal = 'Fail'
        wiringpi.digitalWrite(chlpin, 1)
        return ChlRaw, ChlVolts, ChlCal
    
def readcdom(cdompin, cdomadc,cdomslope, cdomint, cdomchlslope, cdomchlint):
    try:
        #Turn on CDOM probe using relay 
        wiringpi.pinMode(cdompin, 1)
        wiringpi.digitalWrite(cdompin, 0)
        time.sleep(5)
        #read data from ADC chip    
        #read data from ADC Chl 1
        ADC_Chl=cdomadc
        resp=readadc(ADC_Chl,SPICLK,SPIMOSI,SPIMISO,SPICS)
        # Format response from ADC chip
        CDOMRaw = resp
        CDOMVolts = (float(CDOMRaw) / 4095) * 5
        CDOMCal = (CDOMRaw * cdomslope) + cdomint
        CDOMChlEQ = (CDOMRaw * cdomchlslope) + cdomchlint
        print("CDOMRaw is:", CDOMRaw)
        print("CDOMVolts is:", CDOMVolts)
        print("CDOMCal is:", CDOMCal)
        print("CDOM Chl EQ is:", CDOMChlEQ)
        #turn off probe
        wiringpi.digitalWrite(cdompin, 1)
        return CDOMRaw, CDOMVolts, CDOMCal, CDOMChlEQ
    except:
        #print 'Read CDOM Fail'
        CDOMRaw = 'Fail'
        CDOMVolts = 'Fail'
        CDOMCal = 'Fail'
        CDOMChlEQ = 'Fail'
        wiringpi.digitalWrite(cdompin, 1)
        return CDOMRaw, CDOMVolts, CDOMCal, CDOMChlEQ

def readtemp(temppin, tempadc,tempslope, tempint):
    try:
        
        #Turn on chl probe using relay
        wiringpi.pinMode(temppin, 1)
        wiringpi.digitalWrite(temppin, 1)
        time.sleep(5)
        #read data from ADC chip
        #read data from ADC Chl 2
        ADC_Chl=tempadc
        resp=readadc(ADC_Chl,SPICLK,SPIMOSI,SPIMISO,SPICS)
        # Format response from ADC chip
        TempRaw = resp
        TempVolts = (float(TempRaw) / 4095) * 5
        TempCal = (TempRaw * tempslope) + tempint 
        print("TempRaw is:", TempRaw)
        print("TempVolts is:", TempVolts)
        print( "TempCal is:", TempCal)
        #turn off probe
        wiringpi.digitalWrite(temppin, 0)
        return TempRaw, TempVolts, TempCal
    except:
        print( 'Read Temp Fail')
        TempRaw = 'Fail'
        TempVolts = 'Fail'
        TempCal = 'Fail'
        wiringpi.digitalWrite(temppin, 0)
        return TempRaw, TempVolts, TempCal
    
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
        print( "TurbManu value is:", TurbManu)
        print( "TurbCal value is:", TurbCal)
        print( "TurbRaw is:", TurbRaw)
        return TurbRaw, TurbCal, TurbManu
    except:
        print( 'ReadTurbFail')
        TurbRaw = 'Fail'
        TurbCal = 'Fail'
        TurbManu = 'Fail'
        return TurbRaw, TurbCal, TurbManu
def readcond(condpin, condID, conda, condb, condc, condd, tempslope, tempint):
    try:
        wiringpi.pinMode(condpin, 1)
        wiringpi.digitalWrite(condpin, 0)
        time.sleep(5)
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
        CondCal = (CondRaw**3)*conda + (CondRaw**2)*condb + CondRaw*condc + condd    
        #Calculate SpCond and Salinity
        SpCond = CondCal/(1+0.0191*(TempCal-25))
        R = SpCond/53087
        k1 = 0.0120
        k2 = -0.2174
        k3 = 25.3283
        k4 = 13.7714
        k5 = -6.4778
        k6 = 2.5842
        Salinity = k1 +(k2*R**(1/2))+(k3*R)+(k4*R**(3/2))+(k5*R**2)+(k6*R**(5/2))
        #End trace mode
        response = "No"
        while response !="Hi!":
            port.flushInput()
            port.flushOutput()
            for count in range(0, 256):
                port.write(chr(0x01))
            response=port.read(3)
        wiringpi.digitalWrite(condpin, 1)    
        return TempRaw, CondRaw, TempCal, CondCal, SpCond, Salinity
    except:
        #print 'Read Temp/Cond Fail'
        TempRaw = 'Fail'
        CondRaw = 'Fail'
        TempCal = 'Fail'
        CondCal = 'Fail'
        SpCond = 'Fail'
        Salinity = 'Fail'
        wiringpi.digitalWrite(condpin, 1)
        return TempRaw, CondRaw, TempCal, CondCal, SpCond, Salinity
