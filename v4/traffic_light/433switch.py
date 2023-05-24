# Johann Wiesheu / av.wiesheu@bayern-maiol.de / Dec.2022

from gpiozero import LED
from time import sleep
import time
import os
import subprocess
import sys
import datetime

GPIO_RF_SEND = 6
   
def main():   

   if len(sys.argv) != 2:
      #has to be string for later string-compare:
      rotphase = 200
#      print("rPi: no CMD-Line agruemnt found -> 433switch now using default red period of 180 sec. ")
   else:
      rotphase = int((sys.argv[1]))
#      print("rPi: 433switch using rotphase:",rotphase)
   
   #GPIO26 an Pin37:
   led = LED(26)
   
   # play "activating traffic-light" via radio
   os.system('python $HOME/weather_station/tools/enablePTT.py')
   os.system('play -q -v 1.5 $HOME/weather_station/media/de/TL_on.mp3 tempo 1.6 >/dev/null 2>&1')
   os.system('python $HOME/weather_station/tools/disablePTT.py')
   
   # switch on traffic light
   os.system('/home/pilot/.local/bin/rpi-rf_send -g 6  -p 323 -t 1 282961 >/dev/null 2>&1')
   
   # blink LED while traffic light is on
   while rotphase >0:
       led.on()
       time.sleep(0.5)
       led.off()
       time.sleep(0.5)
       rotphase -= 1
   
   # output "deactivating traffic-light" via radio
   os.system('python $HOME/weather_station/tools/enablePTT.py')
   os.system('play -q -v 1.5 $HOME/weather_station/media/de/TL_off.mp3 tempo 1.6 >/dev/null 2>&1')   
   os.system('python $HOME/weather_station/tools/disablePTT.py')
   
   # switch off traffic-light
   os.system('/home/pilot/.local/bin/rpi-rf_send -g 6 -p 323 -t 1 282964 >/dev/null 2>&1')
       
   
   
if __name__ == "__main__":
    main()
