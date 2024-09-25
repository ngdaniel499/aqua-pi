#!/bin/bash

{
    echo "$(date): Starting pump control job"
    source /home/pi/aqua-pi/.venv/bin/activate
    python /home/pi/aqua-pi/python-scripts/run-pump.py
    echo "$(date): Pump control job completed"

} >> "/home/pi/cronrun.log" 2>&1
