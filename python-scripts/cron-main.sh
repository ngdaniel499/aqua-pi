#!/bin/bash
(
    date &&
    echo "Starting job" &&
    source /home/pi/aqua-pi/.venv/bin/activate &&
    echo "Activated venv" &&
    python /home/pi/aqua-pi/python-scripts/main.py &&
    echo "Ran Python script" &&
    python /home/pi/aqua-pi/python-scripts/uploadDataHTTPS.py &&
    echo "Ran Data upload script"
) >> /home/pi/cronrun.log 2>&1
