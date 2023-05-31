###############################################################################
# weather_to_speech.py 
# by Johann Wiesheu
# Mar. 2023 
# Transcoding raw weather data (digits) to speech using local speech sniplets
# Sources of Speach: ~/weather_station/media/<lang>/WSS_<enty>.mp3
################################################################################
# CHANGELOG
# Version 0.3 31 May. 2023
# add error-handling if API call timed out
#
# Version 0.2 17 Apr. 2023
# moved code to function so it can be imported and called by other modules
# solved Problem with exec statement (see below)
# added CMD-line argument "windonly" to call it for transcoding complete 
# weather or wind only
###############################################################################

import argparse
import time
import datetime
from gtts import gTTS
import os
import glob
import sys


def t2s(c):           # return speech for the numbers while parsing weather.txt
    if c == "1":
       return (sniplet_1)
    if c == "2":
       return (sniplet_2)
    if c == "3":
       return (sniplet_3)
    if c == "4":
       return (sniplet_4)
    if c == "5":
       return (sniplet_5)
    if c == "6":
       return (sniplet_6)
    if c == "7":
       return (sniplet_7)
    if c == "8":
       return (sniplet_8)
    if c == "9":
       return (sniplet_9)
    if c == "0":
       return (sniplet_0)
    if c == "-":
       return (sniplet_minus)
    if c == ".":
       return (sniplet_decimal)
    if c == "":
       return ("")

def transcode(lang,scope):
   HOME=os.environ['HOME']
   buffer = [0]*32            # Array for weather data digits
   
   #lang = "de"
   #lang = "en"
   
   weather = HOME + "/weather_station/ramdisk/weather.txt"
   awosfile = HOME + "/weather_station/ramdisk/weather.mp3"
   speechfiles = HOME + "/weather_station/media/" + lang + "/WSS_*.mp3"
   awos = open(awosfile, "wb")
   myTemplate = "{} = {}"
   
   
###############################################################################
#  reading binary contens of all audio files
#  WSS_intro ... WSS_zulu    - magic, magic - 
#  into individual variables wieht name "sniplet_intro" ... "sniplet_zulu"
#  These variables do not work together with a "main()" program structure. 
#  I didn't found why. may be gecause of the local scope of the variables 
#  created by exec statement.
#  17.4.2023: problem solved! pass globals to exec -> https://stackoverflow.com/questions/41100196/exec-not-working-inside-function-python3-x
   
   for file in glob.glob(speechfiles):
#      varname = "sniplet_" + str(file)[38:-4]   # clip filepath up to "_" and ".mp3"  # path for user pi is 3 bytes shorter
      varname = "sniplet_" + str(file)[41:-4]   # clip filepath up to "_" and ".mp3"
#      print("speechfiles: ", file)
#      print("snipletname=", varname)
      with open(file, "rb") as audio:           # read binary
        sniplet = audio.read()
      audio.close()
   
      statement = myTemplate.format(varname, sniplet)
      exec(statement, globals())
###############################################################################
   

###############################################################################
   # parse weather.txt file line by line and transcode digit by digit using t2s()
   f = open( weather, 'r')
   lineno = 0
   for line in f:
      lineno += 1
   
      if lineno == 1:                 # Line 1: check units (metric/imperial)
   #      print("line=", lineno, line.strip())
         if (line.strip() == "imperial"):
            unit = "imperial"
         elif (line.strip() == "metric"):
            unit = "metric"
         else:
            unit = "error"
            awos.write(sniplet_noweather)
            f.close()
            awos.close()
            return

      
      if lineno == 2 and scope == "complete":            # Line 2: intro + time
         awos.write(sniplet_intro)
         for i in range(len(line.strip())):
            buffer[i] = line[i].strip()
   #         print("buffer[i]= ", i, buffer[i])
            if (buffer[i] != ""):
               sniplet = t2s(buffer[i])
               awos.write(sniplet)
         awos.write(sniplet_zulu)
   
      if lineno == 3:                                    # Line 3: wind degree
   #      print("line=", lineno, line.strip())
         awos.write (sniplet_wind)
         for i in range(len(line.strip())):
            buffer[i] = line[i].strip()
   #         print("buffer[i]= ", i, buffer[i])
            if (buffer[i] != ""):
               sniplet = t2s(buffer[i])
               awos.write(sniplet)
         awos.write(sniplet_degree)
        
   
      if lineno == 4:                                    # Line 4 wind knots
   #      print("line=", lineno, line.strip())
         awos.write(sniplet_at)
         for i in range(len(line.strip())):
            buffer[i] = line[i].strip()
   #         print("buffer[i]= ", i, buffer[i])
            if (buffer[i] != ""):
               sniplet = t2s(buffer[i])
               awos.write(sniplet)
         awos.write(sniplet_knot)
   
      if lineno == 5 and scope == "complete":            # Line 5 altimeter
   #      print("line=", lineno, line.strip())
         awos.write(sniplet_altimeter)
         for i in range(len(line.strip())):
            buffer[i] = line[i].strip()
   #         print("buffer[i]= ", i, buffer[i])
            if (buffer[i] != ""):
               sniplet = t2s(buffer[i])
               awos.write(sniplet)
         if unit == "metric":
            awos.write(sniplet_hpa)
   
      if lineno == 6 and scope == "complete":            # Line 6 temperature
   #      print("line=", lineno, line.strip())
         awos.write(sniplet_temp)
         for i in range(len(line.strip())):
            buffer[i] = line[i].strip()
   #         print("buffer[i]= ", i, buffer[i])
            if (buffer[i] != ""):
               sniplet = t2s(buffer[i])
               awos.write(sniplet)
         if unit == "metric":
            awos.write(sniplet_degree)
   
      if lineno == 7 and scope == "complete":            # Line 7 dewpoint
   #      print("line=", lineno, line.strip())
         awos.write(sniplet_dewpoint)
         for i in range(len(line.strip())):
            buffer[i] = line[i].strip()
   #         print("buffer[i]= ", i, buffer[i])
            if (buffer[i] != ""):
               sniplet = t2s(buffer[i])
               awos.write(sniplet)
         if unit == "metric":
            awos.write(sniplet_degree)
   
   f.close()
   awos.close()
   

def main():
   # CMD line arguments
   p=argparse.ArgumentParser()
   p.add_argument('-lang', required=True, choices=['en', 'uk', 'de', 'it'], help='Required: Language for transcoding Weather Options are \"en\", \"uk\", \"de\" and \"it".')
   p.add_argument('-windonly',action='store_true', help='Optional: transcodes only wind data.')
   args = p.parse_args()
   lang = args.lang

   if args.windonly:
      transcode(lang, "windonly")
   else:
      transcode(lang, "complete")
   

if __name__ == "__main__":
    main()

