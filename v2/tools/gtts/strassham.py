#! /usr/bin/python3.5


from gtts import gTTS
import os 

#os.system("cd /home/pilot/weather_station/tools/gtts; gtts-cli --lang de -f strassham.txt -o strassham.mp3")
os.system("cd /home/pilot/weather_station/tools/gtts; play -q strassham.mp3 tempo 1.2 2>&1  >/dev/null")

