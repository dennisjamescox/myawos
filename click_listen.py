import serial
import time
import os
import subprocess
import sys
import datetime

weatherFile = open('/home/pi/weather_station/weather_station.log', 'a')


WeatherMatchString = "Play Weathe"
ErrorString =        "Weather Rep"

last_time_played = 0

ser = serial.Serial('/dev/ttyACM0', 9600)

flush_counter = 0

while True:
    cc = str(ser.readline())
    cc = cc[2:][:11]
    current_time = datetime.datetime.now()
    print(current_time,cc, file = weatherFile)
    flush_counter += 1

    if flush_counter > 25:
        flush_counter = 0
        weatherFile.flush()
    
    if(cc == WeatherMatchString):
        if(last_time_played == 0):
          last_time_played = current_time
        print(current_time,"play full weather report",file = weatherFile)
        os.system('python /home/pi/weather_station/enablePTT.py')
        os.system('aplay /home/pi/weather_station/current.wav')
        os.system('python /home/pi/weather_station/disablePTT.py')
        print(current_time,"weather report complete", file = weatherFile)
        weatherFile.flush()
    elif(cc == ErrorString):
        print(current_time,"Error with Weather Reporting", file = weatherFile)
        weatherFile.flush()

weatherFile.close()        

    




