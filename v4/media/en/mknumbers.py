# generate (US-English) speach for numbers and phrases for weather announcement
# source: local file "numbers.txt"
# destination: WeatherStationSpeachSniplet_<entry>.mp3
# gtts libraries needed: sudo pip3 install gTTS

from gtts import gTTS
import os

lang = "en"            # language model of gTTS

HOME=os.environ['HOME']

numbers = open("numbers.txt", "r")
while True:
    in_line = numbers.readline()
    if not in_line:
        break
    in_line = in_line[:-1]
    file, sniplet = in_line.split(",")
    print("Line:", file, sniplet)
    awos=HOME + "/weather_station/media/" + lang + "/" + file + ".mp3"
    print("generiere ", awos)
    audio=gTTS(sniplet, lang=lang, tld="us")
    audio.save(awos)

numbers.close()
