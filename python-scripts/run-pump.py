import configparser
import time
import wiringpi2 as wiringpi
import os

def read_config():
    config = configparser.ConfigParser()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = 'Upconfig.cfg'
    config_file_path = os.path.join(current_dir, config_file)
    config.read(config_file_path)
    return config

def run_pump(pump_pin, duration):
    wiringpi.wiringPiSetupGpio()
    wiringpi.pinMode(pump_pin, 1)
    wiringpi.digitalWrite(pump_pin, 1)
    print(f"Pump started. Running for {duration} seconds.")
    time.sleep(duration)
    wiringpi.digitalWrite(pump_pin, 0)
    print("Pump stopped.")

def main():
    config = read_config()

    try:
        pumprun = config.get('Section1', 'pumprun').lower()
        pumptime = config.getint('Section1', 'pumptime')
        pumppin = config.getint('Section1', 'pumppin')
    except configparser.NoOptionError as e:
        print(f"Error: Missing configuration option. {e}")
        return
    except ValueError as e:
        print(f"Error: Invalid configuration value. {e}")
        return

    if pumprun == "timed":
        run_pump(pumppin, pumptime)
    elif pumprun == "on":
        wiringpi.wiringPiSetupGpio()
        wiringpi.pinMode(pumppin, 1)
        wiringpi.digitalWrite(pumppin, 1)
        print("Pump is always on.")
    elif pumprun == "off":
        wiringpi.wiringPiSetupGpio()
        wiringpi.pinMode(pumppin, 1)
        wiringpi.digitalWrite(pumppin, 0)
        print("Pump is off.")
    else:
        invalid_value = pumprun
        print(f"Invalid pumprun value: '{invalid_value}'. Expected 'timed', 'on', or 'off'.")

if __name__ == "__main__":
    main()