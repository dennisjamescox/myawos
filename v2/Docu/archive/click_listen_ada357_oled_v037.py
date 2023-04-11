##############################################################################
#
# click_listen_ada357.py
#
# rPi Python code for reading Click-Count at Adafruit ADS1115 A/D converter,
# connected to rPi I2C Bus
#
# Source by Dennis Cox / dennisjcox@gmail.com / 2022
# and Johann Wiesheu / av.wiesheu@bayern-mail.de / Jan. 2023
#
##############################################################################
# CHANGELOG
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

import argparse
import time
import os
import sys
import statistics
from datetime import datetime
import Adafruit_ADS1x15     # Import the ADS1x15 module.

HOME=os.environ['HOME']
current_date = time.strftime("%G-%m-%d")
Prog_Path = HOME + "/weather_station"
logfilename = current_date + "_weather_station.log"
logfilepath = HOME + "/weather_station/ramdisk/"
logfile = logfilepath + logfilename
print('Logfile = ', logfile)
l = open(logfile, 'w')


def read_cmdline():
    p=argparse.ArgumentParser()
    p.add_argument('-triggerlevel',type = int, help='Optional: Triggerlevel at which a Speaker Signal should be interpreted as a Click - assume 15000 should be a good starting value; 15000 is default')
    p.add_argument('-triggeradaption', type = float, help='Optional: allows adapiton of TRIGGERLEVEL by factor. eg. 0.6 / "1.0" or omthis witch completely for OFF')
    p.add_argument('-loghit',action='store_true', help='Optional: logs every recognized PTT hit, including signal level to logfile')
    p.add_argument('-logweather',action='store_true', help='Optional: logs the transmitted weather to logfile')
    p.add_argument('-trafficlight',type = int, help='Optional: Endurance of RED traffic light in seconds; 180 sec. default if omited')
    p.add_argument('-PTTseconds',type = int, help='Optional: Timeout for n Clicks; 5 sec. default if omited')
    p.add_argument('-oled',action='store_true', help='Optional: use little OLED display')
    args=p.parse_args()
    return args 


def main():   
   args=read_cmdline()

   # Choose a gain of 1 for reading voltages from 0 to 4.09V.
   # Or pick a different gain to change the range of voltages that are read:
   #  - 2/3 = +/-6.144V
   #  -   1 = +/-4.096V
   #  -   2 = +/-2.048V
   #  -   4 = +/-1.024V
   #  -   8 = +/-0.512V
   #  -  16 = +/-0.256V
   # See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
   # =>
   # for GAIN = 1,  the Output Signal is calculated as:
   # Output: Max-Signal (4.096V) : 0x7FFF (32767d) 
   #         0V: 0x000 
   #         Min-Signal (-4,096V): 0x8000 
   # Minimal resolution (0x0001) = dU = 0.000125V
   dU = 3.096 / 32767
   GAIN = 1
   
   Channel = 0
   sample = 0
   value = 0
   N = 10                   # n values for median calculation
   lastvalues = [0]*N       # Array for median calculation
   peak = 0
#   adaptTRGlevel = 0        # if "1", one time active (at the end of the first PTT), active when "1", default not active
#   TRG_ATTENUATION = 1.0    # Reduction of Triggerlevel for dropping High-Level

   if args.triggerlevel:
      TRIGGERLEVEL = args.triggerlevel
   else:
      TRIGGERLEVEL = 15000  # Caution with Icom handheld: absolute signal level drops click by click

   if args.triggeradaption:
      adaptTRGlevel = 1 
      TRG_ATTENUATION = args.triggeradaption
   else:
      adaptTRGlevel = 0
      TRG_ATTENUATION = 1

   if args.trafficlight:
      REDTIME = args.trafficlight
   else:
      REDTIME = 180

   if args.PTTseconds:
      PTTseconds = args.PTTseconds      # wait n seconds for Clicks
   else:
      PTTseconds = 5                    # wait 5 seconds for Clicks

   if args.oled:
      OLED = 1                          # activate and use OLED display via queu communication
   else:
      OLED = 0

   LOW1 = 0
   HIGH = 0
   LOW2 = 0
   LHL = 0
   
   diffTimeFlag = 0
   diffTime = 0
   last_time_played = 0
   PTTClickCount = 0
   ClickSuccessFlag = 0
   flushcount = 0

   ### CAUTION: One or more of these values must be set ###
   #
   # Set this value to 1 to allow for 3 click support #
   THREECLICK = 1
   
   # Set this value to 1 to allow for 5 click support #
   FIVECLICK = 1
   
   # Set this value to 1 to allow for 7 click support #
   SEVENCLICK = 1

   ThreeClickMatch= 3
   FiveClickMatch= 5
   SevenClickMatch= 7

   if OLED:
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
      # inter-process-communication queue master to slave and slave to master:
      sq_master, sq_slave = setup_IPC_queue()

      #print("starting OLED-Subsystem at background:")
      os.system('python3 /home/pilot/weather_station/oled/click_display.py &')
      sq_master.put("INIT")          # display snoopy


   TrglvlV = "(="+str(f"{(TRIGGERLEVEL * dU):5.3f}") + "V)"

   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   print("\n================================================================================", file = l)
   print(current_time, "rPi: starting Adafruit PTT-Listener >>",sys.argv[0], "<<\n  using Triggerlevel", TRIGGERLEVEL, TrglvlV, "with TRG-Adaption factor:", TRG_ATTENUATION, "\n  RED-time:", REDTIME, "sec.", "; PTTseconds:", PTTseconds, "sec.", "; HIT-Logging:", args.loghit, "; Logweather:", args.logweather, "; Use-OLED:", args.oled, file = l) 
   print("--------------------------------------------------------------------------------", file = l)
   l.flush()


   # Create an ADS1115 ADC (16-bit) instance at Address 0x48,Bus 1.
   adc = Adafruit_ADS1x15.ADS1115(address=0x48, busnum=1)
   
   # setup Adafruit board for reading Channel 0
   adc.start_adc(0,gain=GAIN)

   if(OLED):
      sq_master.put("WAIT")          # display "wait for PTT"
   
   # Main loop.
#   print('Reading ADS1115 values, press Ctrl-C to quit...')
   while True:
       # Read ADC channel 0 (continously)
       lastvalues[0] = adc.get_last_result()
       sample +=1
       for i in range(N-1,-1,-1):
          lastvalues[i] = lastvalues[i-1]
       mean = statistics.mean(lastvalues)
       flushcount +=1
   
       if mean < TRIGGERLEVEL:
          LOW1 = 1
       if LOW1 == 1:
          if mean > TRIGGERLEVEL:   # scanning for rising edge...
             HIGH += 1              # incement counter für HIGH Level sample, just to know how long PTT was held when debugging
             if mean > peak:
                peak = mean
   
       if LOW1 == 1 and HIGH > 0:    # rising edge detected, scanning for falling edge...
             if mean < TRIGGERLEVEL:
                LOW2 = 1
                if adaptTRGlevel == 1:
                   adaptTRGlevel = 0
                   TRIGGERLEVEL = peak * TRG_ATTENUATION # !!!! Icom Handheld: absolute level of click falls click by click !!!!
   
       if LOW1 and HIGH and LOW2:   # rising and falling edge recognized -> complete click
          PTTClickCount +=1
          LHL = 2

          message = "HIT_" + f"{round(peak):5d}" + " / " +f"{(peak*dU):5.3f}" + "V / TL" + f"{TRIGGERLEVEL:5.3f}"
#          print("message=",message)
          if(OLED):
             sq_master.put(message)                 # display HIT values at OLED

          if args.loghit:
             current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
             print(current_time,"rPi: HIT --- Max-Signal(mean):", round(peak), "=",  "{:.3f}".format(peak*dU), "V /", 
                   "Triggerlevel:", round(TRIGGERLEVEL), "=", "{:.3f}".format(TRIGGERLEVEL * dU), "V", file = l)

          # debugging or measurement of speaker level:
#          current_time = datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")
#          print(f'{current_time}, {round(mean):06}, {sample:06}, {LOW1}, {HIGH}, {LHL}, {PTTClickCount}, {round(TRIGGERLEVEL):05}, {round(peak):05}',  file = l)
#          l.flush()
          LOW1 = 0
          LOW2 = 0
          HIGH = 0
          LHL = 0
          sample = 0
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
                if(OLED):
                   sq_master.put("WAIT")               # display "wait for PTT" at the OLED

             # do the job for 3/5/7 Clicks:
             # 
             if(ClickSuccessFlag == ThreeClickMatch):
                if(OLED):
                   sq_master.put("RED")                # display "Trafficlight ON"
                threeclicks(REDTIME)
                if(OLED):
                   sq_master.put("WAIT")               # display "wait for PTT" at the OLED

             if(ClickSuccessFlag == FiveClickMatch):
                if(OLED):
                   sq_master.put("PTT_get weather data")               # display "get weather data" at the OLED
                   sq_master.put("TX")               # display "wait for PTT" at the OLED
                compare_time = time.time()
                last_time_played = fiveclicks(args.logweather, last_time_played, compare_time)
                if(OLED):
                   sq_master.put("WAIT")               # display "wait for PTT" at the OLED

             if(ClickSuccessFlag == SevenClickMatch):
                if(OLED):
                   sq_master.put("SO")                 # display "Trafficlight ON"
                sevenclicks()
                if(OLED):
                   sq_master.put("WAIT")                 # display WAIT values at OLED
   
             # reset variables
             adaptTRGlevel = 0
             count = 0
             PTTClickCount = 0
             ClickSuccessFlag = 0
             diffTime = 0
             boardTime = 0
             diffTimeFlag = 0

   
       # Pause
       time.sleep(0.005)
   
   adc.stop_adc()
   

def threeclicks(REDTIME):
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   print(current_time,"rPi: Do the job for 3 Click match:",file = l)
   print(current_time,"rPi: switch traffic light on for", REDTIME, "sec.",file = l)
   os.system('python {}/traffic_light/433switch.py {}'.format(Prog_Path, REDTIME))
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   print(current_time,"rPi: switch traffic light off", file = l)
   l.flush()

def fiveclicks(logweather, last_time_played, compare_time):
   if(last_time_played == 0):
      last_time_played = compare_time
      current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
      print(current_time,"rPi: Do the job for 5 Click match:",file = l)
      # print(current_time,"rPi: transmit current weather/AWOS information",file = l)
      print(current_time,"rPi: calling play_weather 0 time on last_time_played",file = l)
      os.system('python {}/ecowitt/ecowitt_weather.py'.format(Prog_Path))
      os.system('python {}/enablePTT.py'.format(Prog_Path))
      os.system('play {}/ramdisk/weather.mp3 tempo 1.2 >/dev/null 2>&1'.format(Prog_Path))
      os.system('python {}/disablePTT.py'.format(Prog_Path))
      current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
      if logweather:
         w = open(Prog_Path + "/ramdisk/weather.txt")
         wd = open(Prog_Path + "/ramdisk/weather_digits.txt")
         weather = w.read().splitlines()
         weatherDigits = wd.read().splitlines()
         print(current_time, "original     :", weatherDigits, file = l)
         print(current_time, "gTTS prepared:", weather, file = l)
         w.close()
         wd.close()
      print(current_time,"rPi: weather report complete", file = l)
      l.flush()

          # If we played the weather make sure there is a 30 second break
   elif(compare_time > (last_time_played + 30)):
      # add a longer break next time
      last_time_played = compare_time + 60
      current_time = time.strftime("%G-%m-%d %T")
      print(current_time,"rPi: calling play_weather N time on last_time_played",file = l)
      os.system('python $HOME/weather_station/ecowitt/ecowitt_weather.py')
      os.system('python $HOME/weather_station/enablePTT.py')
#        os.system('aplay $HOME/weather_station/current.wav')    # play weather, prepared pregulary in background by cron  
      os.system('play $HOME/weather_station/ramdisk/weather.mp3 tempo 1.2 >/dev/null 2>&1')
      os.system('python $HOME/weather_station/disablePTT.py')
      if logweather:
         w = open(Prog_Path + "/ramdisk/weather.txt")
         weather = w.read().splitlines()
         print(weather, file = l)
         w.close()
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

def sevenclicks():
   current_time = datetime.now().strftime("%Y%m%d %H:%M:%S")
   print(current_time,"rPi: Do the job for 7 Click match:",file = l)
   print(current_time,"rPi: special order!",file = l)
   os.system('python {}/gtts/strassham.py'.format(Prog_Path))
#  os.system('python {}/gtts/fortune.py'.format(Prog_Path))
   l.flush()

if __name__ == "__main__":
   main()
   m.shutdown()
   
