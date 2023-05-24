DATUM=`date "+%Y-%m-%d"`
datime=`date "+%Y-%m-%d %H:%M:%S"`
file="${DATUM}_weather_station.log"
logfile="/home/pilot/weather_station/logs/system.log"
msg="$datime rPi-cron: kill process weather_station"

sudo -u pilot -g pilot echo $msg >>${logfile}

sudo pkill -f "click_messenger"
sudo pkill -f "click_listen"
sudo pkill -f "start-stop"
sudo pkill -f "traffic_light"

# USB not used anymore for PTT click count (now natively at rPi, using ADS1115)
#echo "$datime rPi-cron: restart Arduino at USB bus" >> "$logfile"
#/home/pilot/uhubctl/usb-pwr-off.sh
#/home/pilot/uhubctl/usb-pwr-on.sh
