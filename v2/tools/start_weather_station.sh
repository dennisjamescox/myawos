#!/bin/sh

logfile="/home/pilot/weather_station/logs/system.log"

touch $logfile
sudo chown pilot $logfile
sudo chgrp pilot $logfile

# echo some booting information to logfile
sudo -H -u pilot -g pilot /home/pilot/weather_station/tools/bootlog.sh 2>&1 >>$logfile
sleep 1

# start also wireguard VPN connection to Johann
sudo -H -u root -g root /etc/wireguard/restart_wg.sh 2>&1 >>$logfile
sleep 1

# start the AWOS weather station
sudo -H -u pilot -g pilot /usr/bin/python3 /home/pilot/weather_station/click_listen357.py -triggerlevel 10000 -triggeradaption 0.8 -trafficlight 5 -loghit -logweather -message -source ECOWITT -unit metric -lang de 2>&1 >>$logfile 

