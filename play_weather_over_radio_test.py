import serial
import time
import os
import subprocess
import sys


print("play full weather report")
os.system('python /home/pi/weather_station/enablePTT.py')
os.system('aplay /home/pi/weather_station/current.wav')
os.system('python /home/pi/weather_station/disablePTT.py')




    




