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
        pumprun = config.getboolean('Section1', 'pumprun')
        pumptime = config.getint('Section1', 'pumptime')
        pumppin = config.getint('Section1', 'pumppin')
    except configparser.NoOptionError as e:
        print(f"Error: Missing configuration option. {e}")
        return
    except ValueError as e:
        print(f"Error: Invalid configuration value. {e}")
        return

    if pumprun:
        run_pump(pumppin, pumptime)
    else:
        print("pumprun in Upconfig.cfg is set to false")

if __name__ == "__main__":
    main()