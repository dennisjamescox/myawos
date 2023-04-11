DATUM=`date "+%Y-%m-%d"`
datime=`date "+%Y-%m-%d %H:%M:%S"`
file="${DATUM}_weather_station.log"
logfile="/home/pilot/weather_station/logs/system.log"
msg="$datime rPi-cron: rebooting the system"

sudo -u pilot -g pilot echo $msg >>${logfile}

sudo reboot now
