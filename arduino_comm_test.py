import serial
import time
import os
import subprocess
import sys


weatherFile = open('/home/pi/weather_station/weather_station.log', 'w')


WeatherMatchString = "Play Weathe"
ErrorString =        "Weather Rep"

ser = serial.Serial('/dev/ttyACM0', 9600)

while True:
    cc = str(ser.readline())
    cc = cc[2:][:11]
    print(cc, file = weatherFile)
    
    if(cc == WeatherMatchString):
        print("play full weather report", file = weatherFile)
        os.system('python /home/pi/weather_station/enablePTT.py')
        os.system('aplay /home/pi/weather_station/current.wav')
        os.system('python /home/pi/weather_station/disablePTT.py')
        print("weather report complete", file = weatherFile)
    elif(cc == ErrorString):
        print("Error with Weather Reporting", file = weatherFile)

weatherFile.close()        

    




