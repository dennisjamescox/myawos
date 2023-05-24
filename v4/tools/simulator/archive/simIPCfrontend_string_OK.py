##############################################################################
#
# simIPCfrontend.py
#
# simulates frontend of IPC Queue like in click_listen357.py for test purpose
#
##############################################################################
# CHANGELOG
# Version 0.1 22/Feb/2023

import time
import os
import sys
import statistics
from datetime import datetime
from multiprocessing.managers import BaseManager
import queue


def setup_IPC_queue():
   queue_master = queue.Queue()
   queue_slave = queue.Queue()
   BaseManager.register('queue_master', callable=lambda: queue_master)
   BaseManager.register('queue_slave', callable=lambda: queue_slave)
   m = BaseManager(address=('', 50000), authkey=b'AWOS')
   m.start()
   return(m.queue_master(), m.queue_slave())

def main():   

     sq_master, sq_slave = setup_IPC_queue()

     print("starting MESSENGER-Subsystem at background")
     os.system('python3 /home/pilot/weather_station/messenger/click_messenger.py &')

     print("waiting for input to send via IPC queue:")


     while 1:
      text = input("input please:")
      displaytext = "OLED096&TEST&" + text
      displaytext2 = "EMAIL&av.wiesheu@bayern-mail.de&Q-simulation&" + text

      sq_master.put(displaytext)          # display input
      sq_master.put(displaytext2)          # send email


if __name__ == "__main__":
   main()
   m.shutdown()
   
