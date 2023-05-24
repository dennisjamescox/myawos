import serial
import time
import os
import subprocess
import sys


print("play full weather report")
os.system('python /home/pilot/weather_station/tools/enablePTT.py')
os.system('aplay /home/pilot/weather_station/ramdisk/current.wav')
os.system('python /home/pilot/weather_station/tools/disablePTT.py')




    




