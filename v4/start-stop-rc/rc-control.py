#!/usr/bin/env python3
# Johann Wiesheu / av.wiesheu@bayern-mail.de / Dec.2022

from gpiozero import LED
import argparse
import signal
import os
import sys
import time
import logging

from rpi_rf import RFDevice

#GPIO13 an Pin33:
led = LED(13)
blinker = 5
rfdevice = None
RC_A_on  = 279889   # Traffic light 180 sec.
RC_A_off = 279892   # Traffic light 300 sec.
RC_D_off = 283924   # Shutdown

HOME=os.environ['HOME']
current_date = time.strftime("%G-%m-%d")
logfilename = current_date + "_remote_control.log"
logfilepath = HOME + "/weather_station/ramdisk/"
logfile = logfilepath + logfilename
# print('Logfile = ', logfile)
l = open(logfile, 'a')


# on when rPi is running
led.on()

# pylint: disable=unused-argument
def exithandler(signal, frame):
    rfdevice.cleanup()
    sys.exit(0)

logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                    format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s', )

parser = argparse.ArgumentParser(description='Receives a decimal code via a 433/315MHz GPIO device')
parser.add_argument('-g', dest='gpio', type=int, default=12,
                    help="GPIO pin (Default: 12)")
args = parser.parse_args()

signal.signal(signal.SIGINT, exithandler)
rfdevice = RFDevice(args.gpio)
rfdevice.enable_rx()
timestamp = None

# debug
# logging.info("Listening for codes on GPIO " + str(args.gpio))

while True:
    if rfdevice.rx_code_timestamp != timestamp:
        timestamp = rfdevice.rx_code_timestamp

# debug
#        logging.info(str(rfdevice.rx_code) +
#                     " [pulselength " + str(rfdevice.rx_pulselength) +
#                     ", protocol " + str(rfdevice.rx_proto) + "]")

    if rfdevice.rx_code == RC_D_off:
       # blink LED 
        while blinker >0:
            led.on()
            time.sleep(0.1)
            led.off()
            time.sleep(0.1)
            blinker -= 1
        rfdevice.cleanup()
        current_time = time.strftime("%G-%m-%d %T")
#        print("shutdown-code empfangen", rfdevice.rx_code)
        print(current_time, "rPi: RemoteControl shutdown-code received - shuting down", rfdevice.rx_code, file = l)
        l.flush()
        os.system('sudo shutdown -h now')

    elif rfdevice.rx_code == RC_A_on:
        # traffic-light for 180 seconds
        current_time = time.strftime("%G-%m-%d %T")
#        print("rPi: Traffic light via remote control for 180 seconds")
        print(current_time, "rPi: RemoteControl traffic-light-code 180 sec. received", rfdevice.rx_code, "- switch on traffic light for 180 sec.", file = l)
        l.flush()
        os.system('python3 $HOME/weather_station/traffic_light/433switch.py 180 >/dev/null 2>&1')
        print(current_time, "rPi: RemoteControl timer run off                                             - switch off traffic light", file = l)

    elif rfdevice.rx_code == RC_A_off:
        # traffic-light for 300 seconds
        current_time = time.strftime("%G-%m-%d %T")
#        print("rPi: Traffic light via remote control for 300 seconds")
        print(current_time, "rPi: RemoteControl traffic-light-code 300 sec. received", rfdevice.rx_code, "- switch on traffic light for 300 sec.", file = l)
        l.flush()
        os.system('python3 $HOME/weather_station/traffic_light/433switch.py 300 >/dev/null 2>&1')
        print(current_time, "rPi: RemoteControl timer run off                                             - switch off traffic light", file = l)

    
    time.sleep(0.1)
rfdevice.cleanup()
l.close()
