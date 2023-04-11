#!/bin/sh

logfile="/home/pilot/weather_station/logs/system.log"

touch $logfile
sudo chown pilot $logfile
sudo chgrp pilot $logfile

# use remote Control for start/stop the rPi and manually switchin on the traffic light
sudo -H -u pilot -g pilot /usr/bin/python3 /home/pilot/weather_station/start-stop-rc/rc-control.py -g 12 2>&1 >>$logfile

