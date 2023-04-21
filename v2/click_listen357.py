#! /usr/bin/python3
##############################################################################
#
# click_listen357.py
#
# rPi Python code for reading Click-Count at Adafruit ADS1115 A/D converter,
# connected to rPi I2C Bus
# 3/5/7 clicks are recognized - the corresponding actions are executed
#
# Source by Dennis Cox / dennisjcox@gmail.com / 2022
# and Johann Wiesheu / info@myawos.de / Feb. 2023
#
##############################################################################
# CHANGELOG
# Version 0.91 17/Apr/2023
# using optimized ecowitt_getweather.py and weather_to_speech.py modules
#
# Version 0.90 29/Mar/2023
# reworked transcoding of ecowitt weather, now using local dictionary of speech
# sniplets, which can also be used for transcoding WLL or other weather.
# Local transcoding s much faster than Google Text to Speech (gTTS) 
# -> retired weather_gtts.txt.
# Added Imperial and Metric units to raw weather file weather.txt, 
# added German and Italian language dictionaries for weather transcoding, 
# using gTTS.
#
# Version 0.82 02/Mar/2023
# cleared a calculation error in Trg-Adaption and corected a typo, which 
# prevented Trg-Adaption. Enabled Trigger-level adaption at the first 4 clicks
#
# Version 0.81 27/Feb/2023
# moved some code from main() to functions
#
# Version 0.80 25/Feb/2023
# eliminated some coding errors
# now using IPC queue for sending messages to 'universal' message-broker 
# "click_messenger.py". Keywords: EMAIL, OLED096.
# CMD-line argument "-trafficlight" activates trafficlight only when set for the
# time period added, otherwise recognition of 3 clicks is of.
# Renamed the module to click_listen357.py.
# Moved weather subsystem (wll + ecowitt) to sub folder weather,
# moved en/disablePTT.py to subfolder tools and adopted all sources for.
# Added mandatory choice of weather source: WeatherLink Live (WLL) or Ecowitt 
# Output at OLED display currently coupled to CMD-line argument "-message"
# included enable.py and disable.py as a function.
#
# Version 0.37 29/Jan/2023
# added 0.96" SSD1306 Display for headless operation, inluding CMD-Line Parmeter
# communication with OLED system via queue communication with sub-Process
# click_dispaly.py which awaits these parameters:
# CLEAR, WAIT, RED, HIT <value>, PTT <value>, TX, SO
#
# Version 0.35 20/Jan/2023
# removed programming error about handling of "last_time_played" as local variables
# added value-parameter for CMD-Line parameter 'triggeradaption'
# added CMD-Line parameter for logging weatger data transmitted to logfile
# added CMD-Line parameter for traffic light RED time
# added CMD-Line parameter for Click time (time to recognize n clicks)
#
# Version 0.33 18/Jan/2023
# added CMD-Line parsing 'read_cmdline()' 
# and optional permit of next AWOS transmission within 30sec.
#
# Version 0.3 16/Jan/2023
# renamed it from rpi_ada_click03.py to click_listen_ada357.py and 
# placing it in the "weather_station" directory for reuse of other stuff 
# some minor modification in system-call for traffic light Trigger-Adaption
#
# Version 0.2 14/Jan/2023
# beautified; use environment Variable "$HOME" for Programm- and Logfile-Path
# added jobs for 3/5/7 Clicks
# optimized Trigger-Level adaption (now when falling edge is detected) 
# and factor for adacption.
#
# Version 0.1 13/Jan/2023
# Code now includes rising and falling edge recognition for PTT pressed,
# by comparing median values of signal level
# and Trigger-Level adaption because absolute level of click decreases click 
# by click with Icom radio
##############################################################################

import RPi.GPIO as GPIO
import argparse
import time
import os
import sys
import statistics
from datetime import datetime
import Adafruit_ADS1x15     # Import the ADS1x15 module.
from multiprocessing.managers import BaseManager
import queue


HOME=os.environ['HOME']
current_date = time.strftime("%G-%m-%d")
Prog_Path = HOME + "/weather_station"
logfilename = current_date + "_weather_station.log"
logfilepath = HOME + "/weather_station/ramdisk/"
logfile = logfilepath + logfilename
print('Logfile = ', logfile)
l = open(logfile, 'a')

GPIO_PTT = 5                # GPIO at wich relay for PTT is triggered
GPIO_PTT_LED = 21

unit = "metriec"
lang = "de"

MESSAGE = 0                 # use messenger subsystem click_messenger.py

EMAILADDRESS = "ampel@bayern-mail.de"

class message:              # CLASS for sending data to message broker 'click_messenger'
   def __init__(self):
      pass                  # this way, it is an empty structure, filled at runtime:)
#   def __init__(self, target, address, subject, text):
#      self.target = target
#      self.address = address
#      self.subject = subject
#      self.text = text


def read_cmdline():
    p=argparse.ArgumentParser()
    p.add_argument('-triggerlevel',type=int, help='Optional: Triggerlevel at which a Speaker Signal should be interpreted as a Click - assume 15000 should be a good starting value; 15000 (1.88 V) is default.')
    p.add_argument('-triggeradaption', type=float, help='Optional: allows adapiton of TRIGGERLEVEL by factor. eg. 0.6 / "1.0". Or omit it to witch it completely off.')
    p.add_argument('-loghit',action='store_true', help='Optional: logs every recognized PTT hit, including signal level to logfile.')
    p.add_argument('-logweather',action='store_true', help='Optional: logs the transmitted weather to logfile.')
    p.add_argument('-trafficlight',type=int, help='Optional: Endurance of RED traffic light in seconds; 3 clicks recognition for trafficlight is off, when not set.')
    p.add_argument('-PTTseconds',type=int, help='Optional: Timeout for n Clicks; 5 sec. default if omited')
    p.add_argument('-message',action='store_true', help='Optional: use the MESSENGER subsystem for sending messages to targts like EMAIL and/or an OLED display.')
    p.add_argument('-source', required=True, choices=['WLL', 'ECOWITT'], help='Required: Source of weather data. Valid options are \"WLL\" and \"ECOWITT\".')
    p.add_argument('-unit', required=True, choices=['imperial', 'metric'], help='Required: Imperial or Metric units.')
    p.add_argument('-lang', required=True, choices=['en', 'uk', 'de', 'it'], help='Required: Language for transcoding Weather Options are \"en\", \"uk\", \"de\" and \"it".')
    args=p.parse_args()
    return args 


#msg = message("---","---","---","___")        #inital definition of object "msg"
msg = message()        #inital definition of object "msg" - now an empty structure

def main():   
   global unit
   global lang
   
   args=read_cmdline()

   ### check CMD-line arguments ###
   if args.triggerlevel:
      TRIGGERLEVEL = args.triggerlevel
   else:
      TRIGGERLEVEL = 15000  # Caution with Icom handheld: absolute signal level drops click by click
          
   if args.triggeradaption:
      adaptTRGlevel = 4     # adapt Triggerlevel for the first 4 subsequent clicks
      # if we need to adapt TRG level for all day, reset adaptTRGlevel 
      # to master value after job was done for 3/5/7 clicks
      master_adaptTRGlevel = adaptTRGlevel
      TRG_ATTENUATION = args.triggeradaption
   else:
      adaptTRGlevel = 0
      TRG_ATTENUATION = 1

   if args.trafficlight:
      REDTIME = args.trafficlight
   else:
      REDTIME = 0

   if args.PTTseconds:
      PTTseconds = args.PTTseconds      # wait n seconds for Clicks
   else:
      PTTseconds = 5                    # wait 5 seconds for Clicks

   if args.message:
      MESSAGE = 1                       # activate and use OLED display or email output via queu communication
   else:
      MESSAGE = 0

   SOURCE = args.source                 # source of weather data (WLL | ECOWITT)
   ### END check CMD-line arguments ###

   unit = args.unit
   lang = args.lang


   ### define some more variables
   dU = 4.096 / 32767
   GAIN = 1
   # details about resolution of ADS1116 and quantification delta, see description at boards-folder
   
   Channel = 0              # channel at ADS1115, which has the speaker of the radio
   sample = 0
   value = 0
   N = 10                   # n values for median calculation
   lastvalues = [0]*N       # Array for median calculation
   peak = 0
#   adaptTRGlevel = 0        # if "1", one time active (at the end of the first PTT), active when "1", default not active
#   TRG_ATTENUATION = 1.0    # Reduction of Triggerlevel for dropping High-Level

   LOW1 = 0                             # Low before below Threshold
   HIGH = 0                             # High detected
   LOW2 = 0                             # falling edge
   LHL = 0                              # Low-High-Low = PTT click complete
   REtime = 0                           # timeestamp for rising edge (PTT)
   
   diffTimeFlag = 0
   diffTime = 0
   last_time_played = 0
   PTTClickCount = 0
   ClickSuccessFlag = 0

   ### CAUTION: One or more of these values must be set ###
   #
   # Set this value to 1 to allow for 3 click support #
   
   if REDTIME == 0:
      THREECLICK = 0
   else:
      THREECLICK = 1
   
   # Set this value to 1 to allow for 5 click support #
   FIVECLICK = 1
   
   # Set this value to 1 to allow for 7 click support #
   SEVENCLICK = 1


   ThreeClickMatch = 3
   FiveClickMatch = 5
   SevenClickMatch = 7

   # Create an ADS1115 ADC (16-bit) instance at Address 0x48,Bus 1.
   adc = Adafruit_ADS1x15.ADS1115(address=0x48, busnum=1)
   
   # setup Adafruit board for reading Channel 0
   adc.start_adc(0,gain=GAIN)

   # output startup parameters to logfile:
   TrgLvlVolt = " (="+str(f"{(TRIGGERLEVEL * dU):5.3f}") + "V) "
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   logmsg = ("\n================================================================================\n" +
             current_time + " rPi: starting Adafruit PTT-Listener\n  >>" + sys.argv[0] + "<<\n  " +
             "using Triggerlevel " + str(TRIGGERLEVEL) + TrgLvlVolt + "with TRG-Adaption factor: " + 
             str(TRG_ATTENUATION) + ";\n" + "  RED-time: " + str(REDTIME) + 
             "sec.;" + " PTTseconds: " + str(PTTseconds) + "sec.; " + "HIT-Logging: " + 
             str(args.loghit) + "; Logweather: " + str(args.logweather) + 
             ";\n  use-MESSENGER: " + str(args.message) +  "; Source: " + args.source + 
             "; units: " + args.unit + "; lang: " + args.lang +
             "\n--------------------------------------------------------------------------------")
   print(logmsg, file = l)
   l.flush()


   if MESSAGE:
      # inter-process-communication queue master to slave and slave to master:
      out_queue, in_queue = setup_IPC_queue()
      os.system('python3 /home/pilot/weather_station/messenger/click_messenger.py >>/home/pilot/weather_station/logs/system.log 2>&1 &')
      
      # inform about module start...
      send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "INIT", "no text")    # display snoopy
      send_msg_YN(MESSAGE, out_queue, "EMAIL", EMAILADDRESS, "Strassham: AWOS gestartet", "click_listener gestartet")
      send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "WAIT", "no text")
   else:
      out_queue = "None"          # else send_msg_YN() complains about missing Q-info


   #### Main loop ###
#   print('Reading ADS1115 values, press Ctrl-C to quit...')
   while True:
       for i in range(N-1,-1,-1):    # shift values up (in array)
          lastvalues[i] = lastvalues[i-1]
       # Read ADC channel 0
       lastvalues[0] = adc.get_last_result()
       sample +=1
       mean = statistics.mean(lastvalues)

       isclick, TRIGGERLEVEL, adaptTRGlevel, mean, peak, LOW1, HIGH, LOW2, REtime, pulselength = find_click(TRIGGERLEVEL, adaptTRGlevel,TRG_ATTENUATION, mean, peak, LOW1, HIGH, LOW2, REtime)
       if isclick:
          PTTClickCount +=1
          LHL = 2                   # only for plotting values, other than 0 or 1

          displaytext = f"{round(peak):5d}" + " / " +f"{(peak*dU):5.3f}" + "V / TL" + f"{TRIGGERLEVEL:5.0f}"
          send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "HIT", displaytext)

          if args.loghit:
             log_hitdata(mean, peak, TRIGGERLEVEL, dU, pulselength, l)

          # debugging or measurement of speaker level:
#          plot_hitvalue(mean, sample, LOW1, HIGH, LHL, PTTClickCount, TRIGGERLEVEL, peak, l)

          LOW1 = LOW2 = HIGH = LHL = sample = 0
          peak = 0

       if SEVENCLICK and PTTClickCount == 7:
          ClickSuccessFlag = 7
   
       elif FIVECLICK and PTTClickCount == 5:
          ClickSuccessFlag = 5
   
       elif THREECLICK and PTTClickCount == 3:
          ClickSuccessFlag = 3
          
       if PTTClickCount == 1 and diffTimeFlag == 0: 
          diffTime = time.time()
          diffTimeFlag = 1
   
       if(diffTime > 0):
          boardTime = time.time()
          timedOut = boardTime - diffTime
   
          if(timedOut > PTTseconds):
             if(ClickSuccessFlag > 1):
                current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
                print(current_time, "rPi:", ClickSuccessFlag, "Clicks recognized", file = l)
                l.flush()
             else:
                current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
                print(current_time, "rPi: # of Clicks:", PTTClickCount , "Board-Time:", "{:.0f}".format(boardTime), "Diff:", "{:.0f}".format(diffTime), "Timeout:", "{:.3f}".format(timedOut), "sec." , file = l)
                l.flush()
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "WAIT", "no text")

             # do the job for 3/5/7 Clicks:
             # 
             if(ClickSuccessFlag == ThreeClickMatch):
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "RED", "no text")
                send_msg_YN(MESSAGE, out_queue, "EMAIL", EMAILADDRESS, "Strassham: Ampel ein", "Schalte Ampel auf ROT")
                threeclicks(REDTIME)
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "WAIT", "no text")
                send_msg_YN(MESSAGE, out_queue, "EMAIL", EMAILADDRESS, "Strassham: Ampel AUS", "Schalte Ampel aus")

             if(ClickSuccessFlag == FiveClickMatch):
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "PTT", "get weather data")
#                send_msg_YN(MESSAGE, out_queue, "EMAIL", EMAILADDRESS, "AWOS sendet Wind-Daten", "sende AWOS Wetterdaten")
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "TX", "no text")
                fiveclicks(args.logweather, SOURCE)
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "WAIT", "no text")


             if(ClickSuccessFlag == SevenClickMatch):
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "PTT", "get weather data")
#                send_msg_YN(MESSAGE, out_queue, "EMAIL", EMAILADDRESS, "AWOS sendet Wetterdaten", "sende AWOS Wetterdaten")
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "TX", "no text")
                compare_time = time.time()
                last_time_played = sevenclicks(args.logweather, last_time_played, compare_time, SOURCE)
                send_msg_YN(MESSAGE, out_queue, "DISPLAY", "OLED096", "WAIT", "no text")
   
             # reset variables
             adaptTRGlevel = 0                         # adation only at first click
             count = PTTClickCount = ClickSuccessFlag = 0
             diffTime = boardTime = diffTimeFlag = 0

       # Pause
#       time.sleep(0.005)
       time.sleep(0.01)
   
   adc.stop_adc()


def setup_IPC_queue():
   queue_to_msngr = queue.Queue(False)  # "False", for NOT waiting for click_messenger.py to complet his current job
   queue_from_msngr = queue.Queue()     # but proceede immediately in program flow
   BaseManager.register('queue_to_msngr', callable=lambda: queue_to_msngr)
   BaseManager.register('queue_from_msngr', callable=lambda: queue_from_msngr)
   m = BaseManager(address=('', 50000), authkey=b'AWOS')
   m.start()
   return(m.queue_to_msngr(), m.queue_from_msngr())


def find_click(TRIGGERLEVEL, adaptTRGlevel, TRG_ATTENUATION, mean, peak, LOW1, HIGH, LOW2, REtime):
    if mean < TRIGGERLEVEL:
       LOW1 = 1
    if LOW1 == 1:
       if mean > TRIGGERLEVEL:   # HIGH!
          if HIGH == 0: 
             REtime = time.time()   # recognize Time of first occourance of high level for timing high level
          HIGH += 1              # incement counter for HIGH Level sample, just to know how long PTT was held when debugging
          if mean > peak:
             peak = mean

    if LOW1 == 1 and HIGH > 0:    # we are in HIGH, scanning for falling edge...
          if mean < TRIGGERLEVEL: # falling edge detected
             FEtime = time.time()   # recognize Time of falling edge for timing high level
             LOW2 = 1
             if adaptTRGlevel > 0:
                adaptTRGlevel -= 1
                TRIGGERLEVEL = peak * TRG_ATTENUATION # !!!! Icom Handheld: absolute level of click falls click by click !!!!
    
    if LOW1 and HIGH and LOW2:   # rising and falling edge recognized -> complete click
       is_click = 1
       Hlength = FEtime-REtime
#       print("PTT:   Pulselength = :", Hlength, "peak = ", peak, "mean=", mean, "Triggerlevel = ", TRIGGERLEVEL)
    else:
       is_click = 0
       Hlength = 0

    return(is_click, TRIGGERLEVEL, adaptTRGlevel, mean, peak, LOW1, HIGH, LOW2, REtime, Hlength)

   
def send_msg_YN(MESSAGE, out_queue, target, address, subject, text):
    #  if CMD-line agrument "-message"(= var. MESSAGE)is present, it will send a message to click_message.py
    #  messages to EMAIL and DISPLAY are sent via this routine 
    #  for DISPLAYing information, target and address has to be present (see click_messenger.py)
    if MESSAGE:
       msg.target = target
       msg.address = address
       msg.subject = subject
       msg.text = text

       # debug:
#       print("sending message:", MESSAGE, out_queue, target, address, subject, text)
       out_queue.put(msg)


def log_hitdata(mean, peak, TRIGGERLEVEL, dU, pulselength, l):
    current_time = datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")
    print(current_time, "rPi: HIT --- Max-Signal(mean):", round(peak), "=",  "{:.3f}".format(peak*dU), "V /", 
       "Triggerlevel:", round(TRIGGERLEVEL), "=", "{:.3f}".format(TRIGGERLEVEL * dU), "V, ", "PTT-lengt=", "{:.3f}sec".format(pulselength), file = l)


def plot_hitvalue(mean, sample, LOW1, HIGH, LHL, PTTClickCount, TRIGGERLEVEL, peak, l):
    current_time = datetime.now().strftime("%Y%m%d-%H:%M:%S.%f")
    print(f'{current_time}, {round(mean):06}, {sample:06}, {LOW1}, {HIGH}, {LHL}, {PTTClickCount}, {round(TRIGGERLEVEL):05}, {round(peak):05}',  file = l)
    l.flush()


def log_weatherdata():
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   w = open(Prog_Path + "/ramdisk/weather.txt", 'r')
   weather = w.read().splitlines()
   print(current_time, "raw weather  :", weather, file = l)
   w.close()
   l.flush()


def enablePTT():
#   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
#   print(current_time,"enablePTT", file = l)
#   l.flush()
   GPIO.setwarnings(False)
   GPIO.setmode(GPIO.BCM)
   GPIO.setup(GPIO_PTT, GPIO.OUT, initial=GPIO.LOW)
   GPIO.setup(GPIO_PTT_LED,GPIO.OUT, initial=GPIO.LOW)
   GPIO.output(GPIO_PTT,GPIO.HIGH)       # PTT-Relay
   GPIO.output(GPIO_PTT_LED,GPIO.HIGH)    # PTT-LED

def disablePTT():
#   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
#   print(current_time,"disablePTT", file = l)
#   l.flush()
   GPIO.setwarnings(False)
   GPIO.setmode(GPIO.BCM)
   GPIO.setup(GPIO_PTT_LED,GPIO.OUT)
   GPIO.setup(GPIO_PTT, GPIO.OUT)
   GPIO.output(GPIO_PTT,GPIO.LOW)        # PTT-Relay
   GPIO.output(GPIO_PTT_LED,GPIO.LOW)    # PTT-LED

def threeclicks(REDTIME):
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   print(current_time,"rPi: Do the job for 3 Click match:",file = l)
   print(current_time,"rPi: switch traffic light on for", REDTIME, "sec.",file = l)
   os.system('python {}/traffic_light/433switch.py {}'.format(Prog_Path, REDTIME))
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   print(current_time,"rPi: switch traffic light off", file = l)
   l.flush()

def fiveclicks(logweather, SOURCE):
      current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
      print(current_time,"rPi: Do the job for 5 Click match:",file = l)
      print(current_time,"rPi: transmit current wind information",file = l)

      if SOURCE == "ECOWITT":     # else (WLL), weather file is already prepared by cronjob
         os.system(f'python {Prog_Path}/weather/ecowitt/ecowitt_getweather.py -unit {unit}')
         os.system(f'python {Prog_Path}/weather/weather_to_speech.py -lang {lang} -windonly')
      enablePTT()                    # now included in this module
      os.system('play -q -v 1.2 {}/ramdisk/weather.mp3 tempo 1.8 >/dev/null 2>&1'.format(Prog_Path))
      disablePTT()                   # now included in this module

      if logweather:
         log_weatherdata()

      current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
      print(current_time,"rPi: weather report complete", file = l)
      l.flush()
      return()


def sevenclicks(logweather, last_time_played, compare_time, SOURCE):
   if(last_time_played == 0):
      last_time_played = compare_time
      current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
      print(current_time,"rPi: Do the job for 7 Click match:",file = l)
      # print(current_time,"rPi: transmit current weather/AWOS information",file = l)
      print(current_time,"rPi: calling play_weather 0 time on last_time_played",file = l)
      l.flush()

      if SOURCE == "ECOWITT":     # else (WLL), weather file is already prepared by cronjob
#         os.system('python {}/weather/ecowitt/ecowitt_weather.py'.format(Prog_Path))
         os.system(f'python {Prog_Path}/weather/ecowitt/ecowitt_getweather.py -unit {unit}')
         os.system(f'python {Prog_Path}/weather/weather_to_speech.py -lang {lang}')
#      os.system('python {}/tools/enablePTT.py'.format(Prog_Path))
      enablePTT()                    # now included in this module
      os.system('play -q -v 1.2 {}/ramdisk/weather.mp3 tempo 1.8 >/dev/null 2>&1'.format(Prog_Path))
#      os.system('python {}/tools/disablePTT.py'.format(Prog_Path))
      disablePTT()                   # now included in this module

      if logweather:
         log_weatherdata()

      current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
      print(current_time,"rPi: weather report complete", file = l)
      l.flush()

          # If we played the weather make sure there is a 30 second break
   elif(compare_time > (last_time_played + 30)):
      # add a longer break next time
      last_time_played = compare_time + 60
      current_time = time.strftime("%G-%m-%d %T")
      print(current_time,"rPi: calling play_weather N time on last_time_played",file = l)
      l.flush()

      if SOURCE == "ECOWITT":
         os.system(f'python {Prog_Path}/weather/ecowitt/ecowitt_getweather.py -unit {unit}')
         os.system(f'python {Prog_Path}/weather/weather_to_speech.py -lang {lang}')
#      os.system('python {}/tools/enablePTT.py'.format(Prog_Path))
#         os.system('python $HOME/weather_station/weather/ecowitt/ecowitt_weather.py')
#      os.system('python {}/tools/enablePTT.py'.format(Prog_Path))

      os.system('python $HOME/weather_station/tools/enablePTT.py')
#      enablePTT()        # now included in this module

      os.system('play -v 1.2 $HOME/weather_station/ramdisk/weather.mp3 tempo 1.8 >/dev/null 2>&1')
#      os.system('python $HOME/weather_station/tools/disablePTT.py')
      disablePTT()        # now included in this module

      if logweather:
         log_weatherdata()

      current_time = time.strftime("%G-%m-%d %T")
      print(current_time,"rPi: weather report complete", file = l)
      l.flush()

   # we are in possible runaway
   else:
       # but only if CMD-Line Argument "allowfrequentcall" is not set
       runaway_flag = 1
       current_time = time.strftime("%G-%m-%d %T")
       print(current_time,"rPi: Possible runaway - delaying 90 seconds", file = l)
       l.flush()
       last_time_played = compare_time + 60

   return(last_time_played)


if __name__ == "__main__":
   main()
   GPIO.cleanup()
   m.shutdown()
   
