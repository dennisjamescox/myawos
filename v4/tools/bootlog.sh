DATUM=`date "+%Y-%m-%d"`
datime=`date "+%Y-%m-%d %H:%M:%S"`
file="${DATUM}_weather_station.log"
logfile="/home/pilot/weather_station/logs/system.log"

logmessage="$datime booting rPi AWOS weather station"
#echo $logmessage

sudo -H -u pilot echo $logmessage >>$logfile

sudo chown pilot $logfile
sudo chgrp pilot $logfile

