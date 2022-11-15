#!/bin/sh
/usr/bin/python /home/pi/weather_station/weather.py
/usr/bin/perl /home/pi/weather_station/convert_weather_txt_to_wav.pl
sh /home/pi/weather_station/generate.sh



