#! /usr/bin/python3.5


from gtts import gTTS
import os 

s=open("/home/pilot/weather_station/ramdisk/sprueche.txt",'w')
print("Spruch des Tages  . .",file=s)
s.close()
os.system("fortune bahnhof sprueche>> /home/pilot/weather_station/ramdisk/sprueche.txt")

# generate mp3
os.system("gtts-cli --lang de -f /home/pilot/weather_station/ramdisk/sprueche.txt -o /home/pilot/weather_station/ramdisk/sprueche.mp3")
os.system("play -q /home/pilot/weather_station/ramdisk/sprueche.mp3 tempo 1.1 2>&1 >/dev/null")

