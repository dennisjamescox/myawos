#!/bin/sh
/usr/bin/python /home/user/weather_station/weather.py
/usr/bin/perl /home/user/weather_station/convert_weather_txt_to_wav.pl
/usr/bin/perl /home/user/weather_station/convert_weather_txt_to_sms.pl
sh /home/user/weather_station/generate.sh
ffmpeg -loglevel panic -y -i /home/user/weather_station/current.wav -vn -ac 1 -ar 8000 /home/user/weather_camera/current.mp3
cp /home/user/weather_station/current.wav /home/user/weather_camera/current.wav
scp /home/user/weather_station/current.wav weather@10.0.0.122:/home/weather/current.wav
#cp current.mp3 /home/user/Documents/quickstart_folder/static
cp /home/user/weather_station/current_sms.txt /home/user/faa_weather_access
#cp current.mp3 /home/user/faa_weather_access



