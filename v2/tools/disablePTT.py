import RPi.GPIO as GPIO
import os
import time

GPIO_PTT = 5
GPIO_PTT_LED = 21

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PTT,GPIO.OUT)
GPIO.setup(GPIO_PTT_LED,GPIO.OUT)

GPIO.output(GPIO_PTT,GPIO.LOW)
GPIO.output(GPIO_PTT_LED,GPIO.LOW)

