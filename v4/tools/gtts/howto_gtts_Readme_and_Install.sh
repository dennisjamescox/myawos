#!/bin/bash

# Google Text to Speech Interface
# Python libraries and CLI Interface
# install and test gTTS:

pip3 install gTTS
sudo apt-get update && sudo apt-get install sox libsox-fmt-all


#Test the CLI:
echo "Guten Morgen . and . Good Morning" > x.txt
gtts-cli -f x.txt -l de --output x.mp3
play x.mp3 tempo 1.3


#some hints:
# https://stackoverflow.com/questions/70615922/how-to-pause-text-during-speaking-in-gtts
# https://stackoverflow.com/questions/54178646/python-gtts-is-there-a-way-to-change-the-speed-of-the-speech
# https://forums.raspberrypi.com/viewtopic.php?t=261819

# MoD/Spruch des Tages:
# sudo apt-get install cowsay fortunes fortunes-de

