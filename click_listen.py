from gpiozero import LED
import serial
import time
import os
import subprocess
import sys
import datetime
import time


current_date = time.strftime("%G-%m-%d")
logfilename = current_date + "_weather_station.log"
logfilepath = "/home/pi/weather_station/"
logfile = logfilepath + logfilename
print('Logfile = ', logfile)
weatherFile = open(logfile, 'a')


FiveClickMatchString  = "5 Clicks"


last_time_played = 0


# Check which USB-Device you have: $ python -m serial.tools.miniterm
# Original Arduino: /dev/ttyACM0,
# AZ-Delivery: /dev/ttyUSB0
ser = serial.Serial('/dev/ttyACM0', 9600)
#   ser = serial.Serial('/dev/ttyAMA0', 9600)
#   ser = serial.Serial('/dev/ttyUSB0', 9600)

#JW:
ser.flush()
ser.reset_input_buffer()

current_time = time.strftime("%G-%m-%d %T")


flush_counter = 0
# just in case the system goes bonkers
runaway_flag = 0


while True:
   cc = str(ser.readline())
   cc = cc[2:][:-5]
   # used to print out nice time
   current_time = time.strftime("%G-%m-%d %T")
   print(current_time, "Arduino:", cc, file = weatherFile)
      
   # used to make sure we don't play the weather too often
   compare_time = time.time()
   flush_counter += 1
      
      
   if flush_counter > 5:
      flush_counter = 0
      weatherFile.flush()
    
   if(cc == FiveClickMatchString):
      current_time = time.strftime("%G-%m-%d %T")
            
      if(last_time_played == 0):
         last_time_played = compare_time
         print(current_time,"rPi: calling play_weather 0 time on last_time_played",file = weatherFile)
         os.system('python /home/pi/weather_station/enablePTT.py')
         os.system('aplay /home/pi/weather_station/current.wav')
         os.system('python /home/pi/weather_station/disablePTT.py')
         current_time = time.strftime("%G-%m-%d %T")
         print(current_time,"rPi: weather report complete", file = weatherFile)
         weatherFile.flush()

         # If we played the weather make sure there is a 30 second break
      elif(compare_time > (last_time_played + 30)):
         # add a longer break next time
         last_time_played = compare_time + 60
         current_time = time.strftime("%G-%m-%d %T")
         print(current_time,"rPi: calling play_weather N time on last_time_played",file = weatherFile)
         os.system('python /home/pi/weather_station/enablePTT.py')
         os.system('aplay /home/pi/weather_station/current.wav')
         os.system('python /home/pi/weather_station/disablePTT.py')
         current_time = time.strftime("%G-%m-%d %T")
         print(current_time,"rPi: weather report complete", file = weatherFile)
         weatherFile.flush()        # we are in possible runaway
      else:
         runaway_flag = 1
         current_time = time.strftime("%G-%m-%d %T")
         print(current_time,"rPi: Possible runaway - delaying 180 seconds", file = weatherFile)
         weatherFile.flush()
         last_time_played = compare_time + 180
         current_time = time.strftime("%G-%m-%d %T")
         weatherFile.flush()
               

weatherFile.close()        
               
    




