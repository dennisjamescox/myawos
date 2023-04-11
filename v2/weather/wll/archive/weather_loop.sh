#!/bin/sh
/usr/bin/python /home/pilot/weather_station/weather/wll/weather.py
/usr/bin/perl /home/pilot/weather_station/weather/wll/convert_weather_txt_to_wav.pl
sh /home/pilot/weather_station/ramdisk/generate.sh



