import RPi.GPIO as GPIO
import os
import time

#GPIO_PTT = 24
GPIO_PTT = 5
GPIO_PTT_LED = 21

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PTT,GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(GPIO_PTT_LED,GPIO.OUT, initial=GPIO.LOW)

GPIO.output(GPIO_PTT,GPIO.HIGH)
GPIO.output(GPIO_PTT_LED,GPIO.HIGH)
