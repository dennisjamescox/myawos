from gpiozero import LED
import serial
import time
import os
import subprocess
import sys
import datetime
import time
   

def main():   
   if len(sys.argv) != 2:
      #has to be string for later string-compare:
      triggerlevel = "500"
      print("rPi: no CMD-Line agruemnt found -> weather_station now using default Triggerlevel \"500\"")
   else:
      triggerlevel = str(int((sys.argv[1])))
      print("rPi: weather_station using Triggerlevel:",triggerlevel)

   current_date = time.strftime("%G-%m-%d")
   logfilename = current_date + "_weather_station.log"
   logfilepath = "/home/pi/weather_station/ramdisk/"
   logfile = logfilepath + logfilename
   print('Logfile = ', logfile)
   weatherFile = open(logfile, 'a')

   # RTS: ready to read from radio
   # GPIO25 at Pin 22
   RTS = LED(25)
   
   ThreeClickMatchString = "3 Clicks"
   FiveClickMatchString  = "5 Clicks"
   SevenClickMatchString = "7 Clicks"
   
   last_time_played = 0
   
   # Check which USB-Device you have: $ python -m serial.tools.miniterm
   # Original Ardoino: /dev/ttyACM0,
   # AZ-Delivery: /dev/ttyUSB0
   ser = serial.Serial('/dev/ttyACM0', 9600)
#   ser = serial.Serial('/dev/ttyAMA0', 9600)
#   ser = serial.Serial('/dev/ttyUSB0', 9600)

   #JW:
   ser.flush()
   ser.reset_input_buffer()

   current_time = time.strftime("%G-%m-%d %T")
   print(current_time, "rPi: starting PTT-Listener >>",sys.argv[0], "<<  using Triggerlevel " + triggerlevel)
   print(current_time, "rPi: starting PTT-Listener >>",sys.argv[0], "<<  using Triggerlevel " + triggerlevel, file = weatherFile)
   setupArdoino(ser, triggerlevel, weatherFile)

   
   flush_counter = 0
   # just in case the system goes bonkers
   runaway_flag = 0
   
   # RTS: ready to read from radio
   RTS.on() 
   print(current_time, "rPi: RTS=ON", file = weatherFile)

   while True:
       cc = str(ser.readline())
   #    cc = cc[2:][:8]
       cc = cc[2:][:-5]
       # used to print out nice time
       current_time = time.strftime("%G-%m-%d %T")
       print(current_time, "Ardoino:", cc, file = weatherFile)
       
       # used to make sure we don't play the weather too often
       compare_time = time.time()

#      since writing to ramdisk, frequent writes are no problem
#       flush_counter += 1
#       if flush_counter > 10:
#           flush_counter = 0
#           weatherFile.flush()
       weatherFile.flush()
       
       if(cc == FiveClickMatchString):
           current_time = time.strftime("%G-%m-%d %T")
           RTS.off() 
           print(current_time, "rPi: RTS=OFF", file = weatherFile)
           if(last_time_played == 0):
               last_time_played = compare_time
               print(current_time,"rPi: calling play_weather 0 time on last_time_played",file = weatherFile)
               os.system('python /home/pi/weather_station/ecowitt/ecowitt_weather.py')
               os.system('python /home/pi/weather_station/enablePTT.py')
#               os.system('aplay /home/pi/weather_station/current.wav')
               os.system('play /home/pi/weather_station/ramdisk/weather.mp3 tempo 1.2 >/dev/null 2>&1')
               os.system('python /home/pi/weather_station/disablePTT.py')
               current_time = time.strftime("%G-%m-%d %T")
               print(current_time,"rPi: weather report complete", file = weatherFile)
               RTS.on() 
               print(current_time, "rPi: RTS=ON", file = weatherFile)
               weatherFile.flush()
   
               # If we played the weather make sure there is a 30 second break
           elif(compare_time > (last_time_played + 30)):
           # add a longer break next time
               last_time_played = compare_time + 60
               current_time = time.strftime("%G-%m-%d %T")
               print(current_time,"rPi: calling play_weather N time on last_time_played",file = weatherFile)
               os.system('python /home/pi/weather_station/ecowitt/ecowitt_weather.py')
               os.system('python /home/pi/weather_station/enablePTT.py')
#               os.system('aplay /home/pi/weather_station/current.wav')
               os.system('play /home/pi/weather_station/ramdisk/weather.mp3 tempo 1.2 >/dev/null 2>&1')
               os.system('python /home/pi/weather_station/disablePTT.py')
               current_time = time.strftime("%G-%m-%d %T")
               print(current_time,"rPi: weather report complete", file = weatherFile)
               RTS.on() 
               print(current_time, "rPi: RTS=ON", file = weatherFile)
               weatherFile.flush()
           # we are in possible runaway
           else:
               runaway_flag = 1
               current_time = time.strftime("%G-%m-%d %T")
               print(current_time,"rPi: Possible runaway - delaying 90 seconds", file = weatherFile)
               weatherFile.flush()
               last_time_played = compare_time + 60
               RTS.on() 
               current_time = time.strftime("%G-%m-%d %T")
               print(current_time, "rPi: RTS=ON", file = weatherFile)
               weatherFile.flush()
   
       elif(cc == ThreeClickMatchString):
           current_time = time.strftime("%G-%m-%d %T")
           RTS.off() 
           print(current_time, "rPi: RTS=OFF", file = weatherFile)
           print(current_time,"rPi: 3 click match",file = weatherFile)
           print(current_time,"rPi: switch traffic light on",file = weatherFile)
           weatherFile.flush()
# debug       print(current_time,"switch traffic light on")
           os.system('python /home/pi/traffic_light/433switch.py')
           current_time = time.strftime("%G-%m-%d %T")
           print(current_time,"rPi: switch traffic light off", file = weatherFile)
           RTS.on() 
           print(current_time, "rPi: RTS=ON", file = weatherFile)
           weatherFile.flush()

#########  SevenClicks will be used later for opening the hangar, now motd is played #########
       elif(cc == SevenClickMatchString):
           RTS.off() 
           current_time = time.strftime("%G-%m-%d %T")
           print(current_time, "rPi: RTS=OFF", file = weatherFile)
           print(current_time,"rPi: 7 click match",file = weatherFile)
           print(current_time,"rPi: special order!",file = weatherFile)
# debug       print(current_time,"special order")
           os.system('python /home/pi/gtts/strassham.py')
#           os.system('python /home/pi/gtts/fortune.py')
           current_time = time.strftime("%G-%m-%d %T")
           print(current_time,"rPi: special order in preparation", file = weatherFile)
           RTS.on()  
           print(current_time, "rPi: RTS=ON", file = weatherFile)
           weatherFile.flush()
   
   weatherFile.close()

#
#  End main()
#

def setupArdoino(ser, triggerlevel, weatherFile):
   waitforardoino=1
   cmp="Ardoino: Audio Trigger-Level received: " + str(triggerlevel)
#   print("cmp=",cmp)

   while waitforardoino == 1:
#      print("rPi: sending Triggerlevel to Ardoino: ",triggerlevel)
      current_time = time.strftime("%G-%m-%d %T")
      print(current_time, "rPi: sending Triggerlevel to Ardoino:",  triggerlevel, file = weatherFile)
      weatherFile.flush()
      ser.write(str.encode(triggerlevel))
      line = ser.readline().decode('utf-8').rstrip()
#      print("Received from Ardoino: ",line)
      if line == cmp :
         current_time = time.strftime("%G-%m-%d %T")
         print(current_time, line, file = weatherFile)
         weatherFile.flush()
         line = ser.readline().decode('utf-8').rstrip()
#         print("Received from Ardoino: ",line)
         current_time = time.strftime("%G-%m-%d %T")
         print(current_time, line, file = weatherFile)
         weatherFile.flush()
#         print("rPi: Setup Triggerlevel OK, continue main loop")
         print(current_time, "rPi: Setup Triggerlevel OK, continue main loop", file = weatherFile)
         weatherFile.flush()
#         ser.flush()
#         ser.reset_input_buffer()
         waitforardoino = 0
      time.sleep(0.2)
#
# End setupArdoino()
#

if __name__ == "__main__":
    main()
