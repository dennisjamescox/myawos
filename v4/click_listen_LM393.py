#! /usr/bin/python3
##############################################################################
#
# click_listenLM393.py  ---   reduced to the minimum
#
# rPi Python code for reading Click-Count at LM393 1-bit A/D converter,
# 3/5/7 clicks can be recognized - the corresponding actions are executed
#
# Source by Dennis Cox / dennisjcox@gmail.com / 2022
# and Johann Wiesheu / info@myawos.de / Apr. 2023
#
##############################################################################
# CHANGELOG
# Version 1.0 8.May 2023
# reduced to the minimum
# adapted to digital signal Level at KRT2 speaker output: 
# SPKR+ active = 8V, passive = 3 V. Output of LM393 Module = 12V =>
# added Voltage divider to reduce voltage to max 3.3V for GPIO
# option for HIGH-/LOW Active signal - just change the value of "CLICK_ACTIVE" 
# and CLICK_PASSIVE  to change ACTIVE to LOW signal
#
# Version 0.3 17.Apr 2023
# use optimized modules ecowitt_getweather.py and weather_to_speech.py
# now containing Python functions that can be used as imported modules
# instead of using OS Calls
# remaining OS Call is playing the audio file and switching the traffic light
##############################################################################

import RPi.GPIO as GPIO
import time
import argparse
import time
from datetime import datetime
import os
import sys
import ecowitt_getweather
import wll_getweather
import weather_to_speech

HOME=os.environ['HOME']
current_date = time.strftime("%G-%m-%d")
Prog_Path = HOME + "/weather_station"
logfilename = current_date + "_weather_station.log"
logfilepath = HOME + "/weather_station/ramdisk/"
logfile = logfilepath + logfilename
print('Logfile = ', logfile)
lf = open(logfile, 'a')

mp3_file = Prog_Path + "/ramdisk/weather.mp3"
play_audio = "play -q -v 1.2 " + mp3_file + " tempo 1.8 >/dev/null 2>&1"

GPIO_PTT = 5                # GPIO at wich relay for PTT is triggered
GPIO_PTT_LED = 21           # GPIO, connected to Radio control LED
LM393 = 20                  # GPIO, connected to LM393
GPIO.setmode(GPIO.BCM)
GPIO.setup(LM393, GPIO.IN)
GPIO.setwarnings(False)
GPIO.setup(GPIO_PTT, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(GPIO_PTT_LED,GPIO.OUT, initial=GPIO.LOW)

#unit = "imperial"
unit = "metric"
#lang = "en"
lang = "de"

# change HIGH- to LOW-Active
#CLICK_ACTIVE = GPIO.HIGH 
#CLICK_PASSIVE = GPIO.LOW
CLICK_ACTIVE = GPIO.LOW
CLICK_PASSIVE = GPIO.HIGH 

REDTIME = 5           # traffic light RED time
PTTSeconds = 5        # time 5 seconds for reading the clicks
ClickSuccessFlag = 0
diffTime = 0
diffTimeFlag = 0
PTTClickCount = 0
first_high = 0

SEVENCLICK = 7     # de-/activate this option / at least THREECLICK ( x > 0 = TRUE = active)
FIVECLICK = 5      # de-/activate this option / at least THREECLICK ( x > 0 = TRUE = active)
THREECLICK = 3     # de-/activate this option / at least THREECLICK ( x > 0 = TRUE = active)

def log(lf, logtext):
    current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
    print(current_time, "rPi:", logtext, file = lf)
    print(current_time, "rPi:", logtext)
    lf.flush()

def log_weatherdata(lf):
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   w = open(Prog_Path + "/ramdisk/weather.txt", 'r')
   weather = w.read().splitlines()
   print(current_time, "raw weather  :", weather, file = lf)
   w.close()
   lf.flush()

def enablePTT():
#   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
#   print(current_time,"enablePTT", file = lf)
#   lf.flush()
   GPIO.output(GPIO_PTT,GPIO.HIGH)       # PTT-Relay
   GPIO.output(GPIO_PTT_LED,GPIO.HIGH)    # PTT-LED

def disablePTT():
#   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
#   print(current_time,"disablePTT", file = lf)
#   lf.flush()
   GPIO.output(GPIO_PTT,GPIO.LOW)        # PTT-Relay
   GPIO.output(GPIO_PTT_LED,GPIO.LOW)    # PTT-LED


def do_the_job(lf, clicksuccessflag, pttclickcount):
    global unit, lang

    log(lf, "do the job for " + str(clicksuccessflag) + " Clicks / " + 
            "Clicks recognized: " + str(pttclickcount)) 

    if clicksuccessflag == 7:
         log(lf, "rPi: get the weather") 
#         wll_getweather.pull_weather()
         ecowitt_getweather.pull_weather(unit)
         log(lf, "rPi: transcode the weather") 
         weather_to_speech.transcode(lang, "complete")
         enablePTT()
         log(lf, "rPi: play the weather") 
         os.system(play_audio)
         disablePTT()
         log_weatherdata(lf)

    if clicksuccessflag == 5:
         os.system('python {}/traffic_light/433switch.py {}'.format(Prog_Path, REDTIME))

    if clicksuccessflag == 3:
         log(lf, "rPi: get the weather") 
#         wll_getweather.pull_weather()
         ecowitt_getweather.pull_weather(unit)
         log(lf, "rPi: transcode the wind") 
         weather_to_speech.transcode(lang, "windonly")
         enablePTT()
         log(lf, "rPi: play the wind") 
         os.system(play_audio)
         disablePTT()
         log_weatherdata(lf)

def reset_vars():
    global PTTClickCount, ClickSuccessFlag, diffTime, boardTime, diffTimeFlag
    PTTClickCount = ClickSuccessFlag = diffTime = boardTime = diffTimeFlag = 0



try:
   while True:
       rising_edge_time = 0
       falling_edge_time = 0
       if GPIO.input(LM393) == CLICK_PASSIVE:
           pass          # wait for ACTIVE signal
   
       while GPIO.input(LM393) == CLICK_ACTIVE:
           if first_high == 0:
               first_high = 1
               rising_edge_time = time.time()
           pass           # wait fora PASSIVE signal
       falling_edge_time = time.time()    # now we have a complete pulse
       pulse_duration = falling_edge_time - rising_edge_time
   
       if ((pulse_duration >= 0.05) and (pulse_duration < 1)):
           PTTClickCount += 1
           first_high = 0
#           print("PTTClickCount =", PTTClickCount)
       else:
           first_high = 0            # invalid Click (to short or to long)
   
       if(SEVENCLICK and PTTClickCount == 7):
           ClickSuccessFlag = 7
       elif(FIVECLICK and PTTClickCount == 5):
           ClickSuccessFlag = 5
       elif(THREECLICK and PTTClickCount == 3):
           ClickSuccessFlag = 3
   
       if(PTTClickCount == 1 and diffTimeFlag == 0):
           diffTime = time.time();
           diffTimeFlag = 1;
       if(diffTime > 0):
           boardTime = time.time();
           timedOut = boardTime - diffTime;
           if(timedOut > PTTSeconds):
               if(ClickSuccessFlag > 2):
                  do_the_job(lf, ClickSuccessFlag, PTTClickCount)
   
                  reset_vars()
#                  print("continue loop")
               else:
#                  print("timeout PTTs:", PTTClickCount)
                  reset_vars()
#                  print("continue loop")
   
   
       time.sleep(0.01)


except KeyboardInterrupt:
    GPIO.cleanup()

