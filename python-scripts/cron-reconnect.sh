#!/bin/bash

(
    now=$(date +"%m-%d %r")
    wlan='wlan0'
    pingip='google.com'

    echo "$now Checking network connection..."

    /bin/ping -c 2 -I "$wlan" "$pingip" > /dev/null 2>&1
    if [ $? -ge 1 ]; then
        echo "$now Network is DOWN. Performing reset..."
        /sbin/ifdown "$wlan"
        sleep 5
        /sbin/ifup --force "$wlan"
    else
        echo "$now Network is UP. No action required."
    fi
) >> /home/pi/cronrun.log 2>&1
