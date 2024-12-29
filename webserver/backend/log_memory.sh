#!/bin/bash

# Set the log file path
LOG_FILE="/home/ubuntu/aqua-pi-webapp/memory_log.txt"

# Get the current date and time
DATETIME=$(date "+%Y-%m-%d %H:%M:%S")

# Get the process ID of your Gunicorn process
PID=$(pgrep -f gunicorn)

# If multiple PIDs are found, use the first one
PID=$(echo $PID | cut -d' ' -f1)

if [ -z "$PID" ]; then
    echo "$DATETIME - Gunicorn process not found" >> "$LOG_FILE"
    exit 1
fi

# Get memory usage for Gunicorn process
PROCESS_MEMORY=$(ps -o pid,user,%mem,rss,vsz -p $PID | tail -n1)

# Get total system memory
TOTAL_MEMORY=$(free -m | awk '/Mem:/ {print $2 "MB total, " $3 "MB used, " $4 "MB free"}')

# Log the memory usage
echo "$DATETIME - Gunicorn: $PROCESS_MEMORY - System: $TOTAL_MEMORY" >> "$LOG_FILE"
