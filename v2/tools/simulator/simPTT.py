from gpiozero import LED
import serial
import time
import os
import subprocess
import sys
import datetime
import time
   


# GPIO25 at Pin 22
go = LED(5)

# ready to read from handheld
for x in range(9):
   print(x)
   go.on()
   time.sleep(1.40)
   go.off()
   time.sleep(1.40)

