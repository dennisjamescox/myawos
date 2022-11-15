import RPi.GPIO as GPIO
transmit = 21
import os
import time

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(transmit,GPIO.OUT)

GPIO.output(transmit,True)
