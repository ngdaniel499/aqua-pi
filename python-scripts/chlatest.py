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
        while True:
            try:
                window_50 = collections.deque(maxlen=50)
                window_300 = collections.deque(maxlen=300)
                window_1000 = collections.deque(maxlen=1000)
                
                start_time = time.time()

                while time.time() - start_time < 20:
                    # Read and print data
                    resp = readadc(chladc, SPICLK, SPIMOSI, SPIMISO, SPICS)

                    chl_raw = resp
                    chl_volts = (float(chl_raw) / 4095) * 5.0
                    chl_cal = (chl_raw * chlslope) + chlint
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

                    # Append current values to moving average queues
                    window_50.append(chl_cal)
                    window_300.append(chl_cal)
                    window_1000.append(chl_cal)

                    # Calculate moving averages
                    avg_50 = sum(window_50) / len(window_50) if window_50 else 0
                    avg_300 = sum(window_300) / len(window_300) if window_300 else 0
                    avg_1000 = sum(window_1000) / len(window_1000) if window_1000 else 0

                    # Print the data with the moving averages
                    print(f"{timestamp}  {chl_raw:6d}  {chl_volts:8.3f}  {chl_cal:10.3f}   "
                        f"Avg50: {avg_50:10.3f}  Avg300: {avg_300:10.3f}  Avg1000: {avg_1000:10.3f}")
                
                    # Wait for next reading
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
