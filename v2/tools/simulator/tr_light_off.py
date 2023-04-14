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

   
   #GPIO26 an Pin37:
   led = LED(26)
   
   
   # switch off traffic-light
   os.system('/home/pilot/.local/bin/rpi-rf_send -g 6 -p 323 -t 1 282964')
   led.off()
       
   
   
if __name__ == "__main__":
    main()
