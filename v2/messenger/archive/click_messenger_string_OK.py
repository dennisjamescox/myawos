#! /usr/bin/python3
##########################################################################
#
#   click_messenger.py
#
#   Server process for receiving data from master process 
#   via inter-process-communication queue and handling
#   messages to different targets
#
#   by Johann Wiesheu / av.wiesheu@bayern-mail.de / Jan. 2023
#
# VERSION HISTORY
# 28 Feb. 2023: 
# now it is a kind of universal 'message broker' 
#
##########################################################################
import time
import datetime
from multiprocessing.managers import BaseManager
from pathlib import Path
import click_oled096
import click_email


#logfile = "/home/pilot/weather_station/ramdisk/messenger.log"
#l = open(logfile, 'a')

DELIMITER = "&"

def setup_IPC_queue():
   # setup Inter-Process-Communication:
   BaseManager.register('queue_master')
   BaseManager.register('queue_slave')
   m = BaseManager(address=('localhost', 50000), authkey=b'AWOS')
   m.connect()
   return(m)

m = setup_IPC_queue()

# inter-process-communication queue master to slave:
queue_master = m.queue_master()
# inter-process-communication queue slave to master (not used here):
queue_slave = m.queue_slave()

while 1:
   msg = queue_master.get()
   msg = msg.split(DELIMITER)
   target = msg[0]

   if target == "OLED096":
      click_oled096.display_oled096(msg)

   if target == "EMAIL":
      click_email.send_email(msg)

m.shutdown()
#l.close()
