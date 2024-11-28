#!/usr/bin/python
import time
import wiringpi2 as wiringpi
import RPi.GPIO as GPIO
from decimal import *
import configparser as ConfigParser
import os
import sys
import traceback
import collections
import math

# Initialize wiringPi
wiringpi.wiringPiSetupGpio()

# GPIO Setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

SPICLK = 11
SPIMISO = 9
SPIMOSI = 10
SPICS = 8

GPIO.setup(SPIMOSI, GPIO.OUT)
GPIO.setup(SPIMISO, GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS, GPIO.OUT)

GPIO.setup(22, GPIO.OUT) #10x pin
GPIO.setup(27, GPIO.OUT) #100x

def readadc(adcnum, clockpin, mosipin, misopin, cspin):
    if ((adcnum > 7) or (adcnum < 0)):
        return -1

    GPIO.output(cspin, True)
    GPIO.output(clockpin, False)
    GPIO.output(cspin, False)

    commandout = adcnum
    commandout |= 0x18
    commandout <<= 3
    for i in range(5):
        if (commandout & 0x80):
            GPIO.output(mosipin, True)
        else:
            GPIO.output(mosipin, False)
        commandout <<= 1
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)

    adcout = 0
    for i in range(14):
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)
        adcout <<= 1
        if(GPIO.input(misopin)):
            adcout |= 0x1
    GPIO.output(cspin, True)

    adcout >>= 1
    return adcout

def continuous_chl_monitor(config_file='Upconfig.cfg'):
    """
    Continuously monitor chlorophyll sensor readings using configuration from file
    
    Parameters:
    config_file: Path to configuration file (default 'Upconfig.cfg')
    """
    try:
        # Read configuration
        config = ConfigParser.ConfigParser()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        configfilewithpath = os.path.join(current_dir, config_file)
        config.read(configfilewithpath)

        # Get configuration values
        chlpin = config.getint('Section1', 'chlpin')
        chladc = config.getint('Section1', 'chladc')
        chlslope = config.getfloat('Section1', 'chlslope')
        chlint = config.getfloat('Section1', 'chlint')
        readinterval = config.getfloat('Section1', 'readinterval')

        print("Starting continuous chlorophyll monitoring...")
        print(f"Using configuration from: {config_file}")
        print(f"Pin: {chlpin}, ADC: {chladc}, Slope: {chlslope}, Intercept: {chlint}")
        print("\nTimestamp               Raw     Volts    Calibrated")
        print("-" * 50)
        
        # Initial probe setup - turn it on once at the start
        wiringpi.pinMode(chlpin, 1)
        wiringpi.digitalWrite(chlpin, 0)
        time.sleep(readinterval)  # Brief delay for sensor to stabilize
        
        t_sleep = 0.01
        wiringpi.digitalWrite(22, 0)
        wiringpi.digitalWrite(27, 1)
        
        running_mean = 0
        running_std_dev = 0
        n = 0
        
        while True:
            try:
                # Read and print data
                resp = readadc(chladc, SPICLK, SPIMOSI, SPIMISO, SPICS)

                chl_raw = resp
                chl_volts = (float(chl_raw) / 4095) * 5.0
                chl_cal = (chl_raw * chlslope) + chlint
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

                # Update sample count
                n += 1
                
                # Running mean calculation
                running_mean += (chl_cal - running_mean) / n
                
                # Running standard deviation calculation
                running_std_dev += (chl_cal - running_mean) * (chl_cal - running_mean - running_std_dev) / n
                
                # Calculate the standard error of the mean (SEM)
                sem = running_std_dev / math.sqrt(n)
                
                # 95% Confidence Interval (1.96 * SEM for 95% confidence)
                ci_lower = running_mean - 1.96 * sem
                ci_upper = running_mean + 1.96 * sem
                
                # Print the data with running average and confidence interval
                print(f"{timestamp}  {chl_raw:6d}  {chl_volts:8.3f}  {chl_cal:10.3f}   "
                    f"Running Mean: {running_mean:10.3f}  SEM: {sem:10.3f}  "
                    f"CI: ({ci_lower:10.3f}, {ci_upper:10.3f})")

                time.sleep(t_sleep)
                
            except Exception as e:
                print(f"Error reading sensor: {str(e)}")
                print("Retrying in 5 seconds...")
                time.sleep(5)
                continue
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        # Ensure probe is turned off
        wiringpi.digitalWrite(chlpin, 1)
        wiringpi.digitalWrite(22, 0)
        wiringpi.digitalWrite(27, 0)
        GPIO.cleanup()
    except Exception as e:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        error_msg = tbinfo + " " + str(sys.exc_info()[1])
        print(f"Fatal error: {error_msg}")
        wiringpi.digitalWrite(chlpin, 1)  # Make sure to turn off probe on error
        GPIO.cleanup()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        continuous_chl_monitor(config_file)
    else:
        continuous_chl_monitor()
