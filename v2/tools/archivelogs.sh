DATUM=`date "+%Y-%m-%d"`
datime=`date "+%Y-%m-%d %H:%M:%S"`
file="${DATUM}_weather_station.log"
logfile="${HOME}/weather_station/logs/system.log"
echo "$datime rPi-cron: archiving logfiles from ramdisk to \"logs-folder\"" >> "$logfile"
zip -jm ${HOME}/weather_station/logs/$(date +"%Y-%m-%d")_weather_station.log.zip ${HOME}/weather_station/ramdisk/*log

