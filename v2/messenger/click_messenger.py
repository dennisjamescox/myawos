#! /usr/bin/python3
##########################################################################
#
#   click_messenger.py
#
#   Messaging handling process for receiving data from click_listener
#   process via inter-process-communication queue and distributing
#   messages to different targets
#
#   by Johann Wiesheu / av.wiesheu@bayern-mail.de / Jan. 2023
#
# VERSION HISTORY
# 28 Feb. 2023: 
# now a kind of universal 'message broker' 
# data-exchange for receiving data via CLASS 'message'
#
##########################################################################
import time
#import datetime
from datetime import datetime
from multiprocessing.managers import BaseManager
from pathlib import Path
import click_oled096
import click_email


#logfile = "/home/pilot/weather_station/ramdisk/messenger.log"
#l = open(logfile, 'a')

DELIMITER = "&"

class message:                   # class for receiving messages
   def __init__(self, target, address, subject, text):
      self.target = target
      self.address = address
      self.subject = subject
      self.text = text

def setup_IPC_queue():
   # setup Inter-Process-Communication:
   BaseManager.register('queue_to_msngr')
   BaseManager.register('queue_from_msngr')
   m = BaseManager(address=('localhost', 50000), authkey=b'AWOS')
   m.connect()
   return(m)

m = setup_IPC_queue()

# inter-process-communication queue listener to messenger:
queue_from_listener = m.queue_to_msngr()
# inter-process-communication queue messenger to listener (not used here):
queue_to_listener = m.queue_from_msngr()

msg = message("000","0000","00000","000000")

while 1:
   
   msg = queue_from_listener.get()
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
#   print(current_time, " messenger loop - receved:", msg.target, msg.address, msg.subject, msg.text, file = l)
#   l.flush()

   if msg.target == "DISPLAY" and msg.address == "OLED096":
      try:
          click_oled096.display_oled096(msg)
      except:
          current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
          print(current_time, " rPi: display error occoured", msg.target, msg.address, msg.subject, msg.text)

# email currently OoO
   if msg.target == "EMAIL":
      try:
         click_email.send_email(msg)
      except:
          current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
          print(current_time, " rPi: email error occoured", msg.target, msg.address, msg.subject, msg.text)
   time.sleep(0.1)

m.shutdown()
#l.close()
