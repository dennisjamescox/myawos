#! /usr/bin/python3.5


from gtts import gTTS
import os 

s=open("test1.txt",'r')
os.system("gtts-cli --lang en -f test1.txt -o test1.mp3")
os.system("play -q test1.mp3 tempo 1.2")

s.close()
