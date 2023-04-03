###############################################################################
# weather_to_speech.py 
# by Johann Wiesheu
# Mar. 2023 
# Transcoding raw weather data (digits) to speech using local speech sniplets
# Sources of Speach: ~/weather_station/media/<lang>/WSS_<enty>.mp3
###############################################################################

import argparse
import time
import datetime
from gtts import gTTS
import os
import glob
import sys

HOME=os.environ['HOME']
buffer = [0]*32            # Array for weather data digits

#lang = "de"
#lang = "en"

# CMD line arguments
p=argparse.ArgumentParser()
p.add_argument('-lang', required=True, choices=['en', 'uk', 'de', 'it'], help='Required: Language for transcoding Weather Options are \"en\", \"uk\", \"de\" and \"it".')
args = p.parse_args()
lang = args.lang

weather = HOME + "/weather_station/ramdisk/weather.txt"
awosfile = HOME + "/weather_station/ramdisk/weather.mp3"
speechfiles = HOME + "/weather_station/media/" + lang + "/WSS_*.mp3"
awos = open(awosfile, "wb")
myTemplate = "{} = {}"


###############################################################################
#  reading binary contens of all audio files 
#  WSS ... WSS_zulu
#  into individual variables wieht name "sniplet_intro" ... "sniplet_zulu"
#  These variables do not work together with a "main()" program structure. 
#  I didn't found why. may be gecause of the local scope of the variables 
#  created by exec statement.

for file in glob.glob(speechfiles):
   varname = "sniplet_" + str(file)[41:-4]   # clip filepath up to "_" and ".mp3"
#   print("speechfiles: ", file)
#   print("snipletname=", varname)
   with open(file, "rb") as audio:           # read binary
     sniplet = audio.read()
   audio.close()

   statement = myTemplate.format(varname, sniplet)
   exec(statement)
###############################################################################

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
      else:
         unit = "metric"
   
   if lineno == 2:                 # Line 1: intro + time
#      awos.write(sniplet_intro)
      for i in range(len(line.strip())):
         buffer[i] = line[i].strip()
#         print("buffer[i]= ", i, buffer[i])
         if (buffer[i] != ""):
            sniplet = t2s(buffer[i])
            awos.write(sniplet)
      awos.write(sniplet_zulu)

   if lineno == 3:                 # Line 2: wind degree
#      print("line=", lineno, line.strip())
      awos.write (sniplet_wind)
      for i in range(len(line.strip())):
         buffer[i] = line[i].strip()
#         print("buffer[i]= ", i, buffer[i])
         if (buffer[i] != ""):
            sniplet = t2s(buffer[i])
            awos.write(sniplet)
      awos.write(sniplet_degree)
     

   if lineno == 4:                 # Line 3 wind knots
#      print("line=", lineno, line.strip())
      awos.write(sniplet_at)
      for i in range(len(line.strip())):
         buffer[i] = line[i].strip()
#         print("buffer[i]= ", i, buffer[i])
         if (buffer[i] != ""):
            sniplet = t2s(buffer[i])
            awos.write(sniplet)
      awos.write(sniplet_knot)

   if lineno == 5:                 # Line 4 altimeter
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

   if lineno == 6:                 # Line 5 temperature
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

   if lineno == 7:                 # Line 6 dewpoint
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

