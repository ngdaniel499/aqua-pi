import os
import glob
import time
import datetime

import sys
import serial
from serial.tools import list_ports
import traceback
import math
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
GPIO.setup(22, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)

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

def readchl(chlpin, chladc, chlslope, chlint, gain):
    try:
        # Validate gain
        if gain not in {1, 10, 100}:
            print(f"Invalid gain value '{gain}'. Must be '1', '10', or '100'. Exiting.")
            sys.exit(1)

        # Define pin numbers
        TENX_PIN = 22
        HUNDREDX_PIN = 27

        # Turn on chl probe using relay
        wiringpi.pinMode(chlpin, 1)
        wiringpi.digitalWrite(chlpin, 0)

        # Set gain
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
        
        # Allow sensor to stabilize
        time.sleep(5)

        # Initialize variables
        n = 0
        chl_raw_running_mean = 0
        chl_raw_running_variance = 0
        t_sleep = 0.01
        start_time = time.time()

        # Collect data for 3 seconds
        while time.time() - start_time < 3:
            resp = readadc(chladc, SPICLK, SPIMOSI, SPIMISO, SPICS)
            chl_raw = resp
            n += 1

            # Update running mean
            delta = chl_raw - chl_raw_running_mean
            chl_raw_running_mean += delta / n

            # Update running variance (Welford's method)
            chl_raw_running_variance += delta * (chl_raw - chl_raw_running_mean)
            
            time.sleep(t_sleep)

        # Calculate standard deviation
        if n > 1:
            chl_raw_running_std_dev = math.sqrt(chl_raw_running_variance / (n - 1))
        else:
            chl_raw_running_std_dev = 0

        # Calculate SEM and CI
        chl_raw_sem = chl_raw_running_std_dev / math.sqrt(n)
        chl_raw_ci_lower = chl_raw_running_mean - 1.96 * chl_raw_sem
        chl_raw_ci_upper = chl_raw_running_mean + 1.96 * chl_raw_sem

        # Calculate final values
        ChlRaw = chl_raw_running_mean
        ChlVolts = (ChlRaw / 4095) * 5
        ChlCal = (ChlRaw * chlslope) + chlint
        chl_raw_ci_range = chl_raw_ci_upper - chl_raw_ci_lower

        chl_volts_ci_range = (chl_raw_ci_range / 4095) * 5
        chl_volts_sem = (chl_raw_sem / 4095) * 5
        chl_cal_ci_range = (chl_raw_ci_range * chlslope) + chlint
        chl_cal_sem = (chl_raw_sem * chlslope) + chlint

        # Print results
        print("ChlRaw is:", ChlRaw)
        print("ChlVolts is:", ChlVolts)
        print("ChlCal is:", ChlCal)

        # Turn off probe
        wiringpi.digitalWrite(chlpin, 1)

        return (ChlRaw, chl_raw_ci_range, chl_raw_sem, 
                ChlVolts, chl_volts_ci_range, chl_volts_sem, 
                ChlCal, chl_cal_ci_range, chl_cal_sem)

    except Exception as e:
        print(f"Read Chl Fail: {e}")
        
        # Turn off probe and reset pins
        wiringpi.digitalWrite(chlpin, 1)
        wiringpi.digitalWrite(TENX_PIN, 0)
        wiringpi.digitalWrite(HUNDREDX_PIN, 0)

        return ('Fail', 'Fail', 'Fail', 'Fail', 'Fail', 'Fail', 'Fail', 'Fail', 'Fail')
    
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

def readtemp(temppin, tempadc, tempslope, tempint):
    try:
        # Turn on chl probe using relay
        wiringpi.pinMode(temppin, 1)
        wiringpi.digitalWrite(temppin, 1)
        time.sleep(5)  # Allow probe to stabilize
        
        ci_range = 0
        t_sleep = 0.01
        running_variance = 0
        running_mean = 0
        running_std_dev = 0
        n = 0
        
        # Get current timestamp for logging
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Sample loop
        while n < 500:
            # Read data from ADC
            temp_raw = readadc(tempadc, SPICLK, SPIMOSI, SPIMISO, SPICS)
            
            # Update sample count
            n += 1
            
            # Running mean calculation
            running_mean += (temp_raw - running_mean) / n
            
            # Running standard deviation calculation
            running_variance += (temp_raw - running_mean) * (temp_raw - running_mean) / n
            running_std_dev = math.sqrt(running_variance)
            
            # Standard error of the mean (SEM)
            sem = running_std_dev / math.sqrt(n)
            
            # 95% Confidence Interval
            ci_range = 1.96 * sem
            
            time.sleep(t_sleep)

        
        # Calculate voltage and calibrated temperature using parameters
        temp_volts = (float(running_mean) / 4095) * 5.0
        temp_cal = (running_mean * tempslope) + tempint
        temp_cal_ci_range = (ci_range * tempslope) + tempint #Scale the error appropriately
        
        # Print results
        print(f"{n}|{timestamp}|Raw:{running_mean:1.2f}|Volts:{temp_volts:1.2f}|cal:{temp_cal:1.2f}"
              f"|Mean:{running_mean:1.3f}|SEM:{sem:1.1f}"
              f"|CI_range:{ci_range:1.3f}")
        
        # Turn off probe
        wiringpi.digitalWrite(temppin, 0)
        
        return running_mean, temp_volts, temp_cal, temp_cal_ci_range
    except Exception as e:
        print(f'Read Temp Fail: {e}')
        temp_raw = 'Fail'
        temp_volts = 'Fail'
        temp_cal = 'Fail'
        
        # Make sure to turn off the probe even on failure
        wiringpi.digitalWrite(temppin, 0)
        
        return temp_raw, temp_volts, temp_cal
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


def check_serial_ports():
    """Check available serial ports and their details"""
    print("\nDEBUG: Checking available serial ports:")
    ports = list_ports.comports()
    if not ports:
        print("DEBUG: No serial ports found!")
        return
    
    for port in ports:
        print(f"DEBUG: Found port: {port.device}")
        print(f"    Description: {port.description}")
        print(f"    Hardware ID: {port.hwid}")

def readcond(condpin, condID, conda, condb, condc, condd, tempslope, tempint):
    """
    Read temperature and conductivity from sensor with enhanced serial debugging
    """
    port = None
    try:
        print(f"\nDEBUG: Setting up pin {condpin}")
        wiringpi.pinMode(condpin, 1)
        wiringpi.digitalWrite(condpin, 0)
        print("DEBUG: Set pin low, waiting 5 seconds for sensor power-up")
        time.sleep(5)
        
        # Check available serial ports
        check_serial_ports()
        
        print("\nDEBUG: Attempting to open /dev/ttyUSB0")
        try:
            port = serial.Serial("/dev/ttyUSB0", baudrate=4800, bytesize=8, 
                               parity='N', stopbits=1, xonxoff=0, rtscts=0, timeout=10)
            print(f"DEBUG: Serial port opened successfully")
            print(f"DEBUG: Port settings:")
            print(f"    Baudrate: {port.baudrate}")
            print(f"    Port name: {port.name}")
            print(f"    Timeout: {port.timeout}")
            print(f"    Is open: {port.is_open}")
        except serial.SerialException as e:
            print(f"ERROR: Failed to open serial port: {str(e)}")
            raise
        
        # Wake up odyssey sensor
        response = b""
        trycount = 0
        while response != b"Hi!" and trycount < 3:
            print(f"\nDEBUG: Attempting sensor wake up, try {trycount + 1}")
            port.flushInput()
            port.flushOutput()
            
            # Send wake-up byte and verify it was sent
            wake_byte = bytes([0x01])
            bytes_written = port.write(wake_byte)
            print(f"DEBUG: Wrote {bytes_written} byte(s): 0x01")
            
            # Wait briefly for the write to complete
            port.flush()
            
            # Try to read response with explicit timeout
            print("DEBUG: Waiting for response...")
            response = port.read(3)
            print(f"DEBUG: Response received: {response} (length: {len(response)})")
            print(f"DEBUG: Response in hex: {response.hex() if response else 'empty'}")
            
            if not response:
                print("DEBUG: No response received within timeout period")
            
            trycount += 1
            
            if trycount < 3 and response != b"Hi!":
                print("DEBUG: Incorrect response, waiting 1 second before retry")
                time.sleep(1)
        
        if response != b"Hi!":
            raise Exception(f"Failed to wake up sensor after {trycount} attempts")
        
        print("\nDEBUG: Sensor wake-up successful, starting trace mode")
        time.sleep(1)
        port.flushOutput()
        port.flushInput()
        
        trace_bytes = [bytes([0x54]), bytes([0x1a])]
        for b in trace_bytes:
            bytes_written = port.write(b)
            print(f"DEBUG: Wrote trace byte: {b.hex()} ({bytes_written} bytes)")
            port.flush()

        print("\nDEBUG: Reading sensor data")
        data = port.read(4)
        print(f"DEBUG: Read {len(data)} bytes: {data.hex() if data else 'empty'}")
        
        if len(data) != 4:
            raise Exception(f"Expected 4 bytes of data, got {len(data)}")
        
        print(f"DEBUG: Raw data received: {list(data)}")
        
        # Calculate values - data is already bytes in Python 3
        TempRaw = data[0] + data[1]*256
        CondRaw = data[2] + data[3]*256
        
        print(f"DEBUG: Raw values - Temp: {TempRaw}, Cond: {CondRaw}")
        
        # Perform Calibrations
        TempCal = (TempRaw*tempslope) + tempint
        CondCal = (CondRaw**3)*conda + (CondRaw**2)*condb + CondRaw*condc + condd    
        
        print(f"DEBUG: Calibrated values - Temp: {TempCal}, Cond: {CondCal}")
        
        # Calculate SpCond and Salinity
        SpCond = CondCal/(1+0.0191*(TempCal-25))
        R = SpCond/53087
        k1, k2, k3, k4, k5, k6 = 0.0120, -0.2174, 25.3283, 13.7714, -6.4778, 2.5842
        Salinity = k1 + (k2*R**(1/2)) + (k3*R) + (k4*R**(3/2)) + (k5*R**2) + (k6*R**(5/2))
        
        print(f"DEBUG: Calculated values - SpCond: {SpCond}, Salinity: {Salinity}")
        
        # End trace mode
        print("DEBUG: Ending trace mode")
        response = b"No"
        while response != b"Hi!":
            port.flushInput()
            port.flushOutput()
            for count in range(0, 256):
                port.write(bytes([0x01]))
            response = port.read(3)
            
        wiringpi.digitalWrite(condpin, 1)    
        return TempRaw, CondRaw, TempCal, CondCal, SpCond, Salinity
        
    except Exception as e:
        print("\nERROR: Sensor read failed")
        print(f"ERROR: {str(e)}")
        print(f"ERROR: Full traceback:")
        print(traceback.format_exc())
        
        if port:
            try:
                port.close()
                print("DEBUG: Closed serial port")
            except:
                print("ERROR: Failed to close serial port")
                print(traceback.format_exc())
        
        wiringpi.digitalWrite(condpin, 1)
        return 'Fail', 'Fail', 'Fail', 'Fail', 'Fail', 'Fail'
    
    finally:
        if port and port.is_open:
            try:
                port.close()
                print("DEBUG: Closed serial port")
            except:
                print("ERROR: Failed to close serial port in finally block")
                print(traceback.format_exc())

"""
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
"""
