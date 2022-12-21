import serial
import time
import os
import subprocess
import sys
import datetime
import time


weatherFile = open('/home/pi/weather_station/weather_station.log', 'a')


WeatherMatchString = "Play Weathe"
ErrorString =        "Weather Rep"

last_time_played = 0

ser = serial.Serial('/dev/ttyACM0', 9600)

flush_counter = 0
# just in case the system goes bonkers
runaway_flag = 0

while True:
    cc = str(ser.readline())
    cc = cc[2:][:11]
    # used to print out nice time
    current_time = datetime.datetime.now()
    print(current_time,cc, file = weatherFile)
    
    # used to make sure we don't play the weather too often
    compare_time = time.time()
    flush_counter += 1


    if flush_counter > 25:
        flush_counter = 0
        weatherFile.flush()
    
    if(cc == WeatherMatchString):
        if(last_time_played == 0):
            last_time_played = compare_time
            print(current_time,"calling play_weather 0 time on last_time_played",file = weatherFile)
            os.system('python /home/pi/weather_station/enablePTT.py')
            os.system('aplay /home/pi/weather_station/current.wav')
            os.system('python /home/pi/weather_station/disablePTT.py')
            print(current_time,"weather report complete", file = weatherFile)
            weatherFile.flush()

            # If we played the weather make sure there is a 30 second break
        elif(compare_time > (last_time_played + 30)):
        # add a longer break next time
            last_time_played = compare_time + 60
            print(current_time,"calling play_weather N time on last_time_played",file = weatherFile)
            os.system('python /home/pi/weather_station/enablePTT.py')
            os.system('aplay /home/pi/weather_station/current.wav')
            os.system('python /home/pi/weather_station/disablePTT.py')
            print(current_time,"weather report complete", file = weatherFile)
            weatherFile.flush()
        # we are in possible runaway
        else:
            runaway_flag = 1
            print(current_time,"Possible runaway - delaying 90 seconds", file = weatherFile)
            weatherFile.flush()
            last_time_played = compare_time + 60
             
    elif(cc == ErrorString):
        print(current_time,"Error with Weather Reporting", file = weatherFile)
        weatherFile.flush()

weatherFile.close()        

    
    



