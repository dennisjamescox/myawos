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

class message:
   def __init__(self, target, address, subject, text):
      self.target = target
      self.address = address
      self.subject = subject
      self.text = text


def setup_IPC_queue():
   queue_to_msngr = queue.Queue()
   queue_from_msngr = queue.Queue()
   BaseManager.register('queue_to_msngr', callable=lambda: queue_to_msngr)
   BaseManager.register('queue_from_msngr', callable=lambda: queue_from_msngr)
   m = BaseManager(address=('', 50000), authkey=b'AWOS')
   m.start()
   return(m.queue_to_msngr(), m.queue_from_msngr())

def main():   

     out_queue, in_queue = setup_IPC_queue()

#     print("starting MESSENGER-Subsystem at background")
     os.system('python3 /home/pilot/weather_station/messenger/click_messenger.py &')



     msg1 = message("----", "...", "====", "xxxxxxxxxxxx")
     msg2 = message("----", "...", "====", "xxxxxxxxxxxx")

     print("waiting for input to send via IPC queue:")

     while 1:

        text = input("input please:")

        msg1 = message("DISPLAY", "OLED096", "TEST", text)
        msg2 = message("EMAIL", "av.wiesheu@bayern-mail.de", "TEST-CLASS", text)

        out_queue.put(msg1)          # display input
        out_queue.put(msg2)          # send input to email


if __name__ == "__main__":
   main()
   m.shutdown()
   
