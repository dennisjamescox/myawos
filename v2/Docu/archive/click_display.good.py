#! /usr/bin/python3
# -*- coding: utf-8 -*-
##########################################################################
#
#   click_display.py
#
#   Server process for receiving data from master process 
#   via inter-process-communication queue and display them 
#   on OLED 128 x 64 pixel display with SSD1306 driver
#
#   by Johann Wiesheu / av.wiesheu@bayern-mail.de / Jan. 2023
#
##########################################################################
import time
import datetime
from demo_opts import get_device
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw, Image, ImageSequence
from array import*
from multiprocessing.managers import BaseManager
from pathlib import Path
from luma.core.sprite_system import framerate_regulator

#serial = i2c(port=1, address=0x3C)
#device = ssd1106(serial)

#logfile = "/home/pilot/weather_station/ramdisk/oled.log"
#l = open(logfile, 'a')

N = 5                   # n values for scrolling
line = [0]*N            # Array for scrolling

device = get_device()   # get parameters of installed OLED device

def init_array():
   line[0] = "                           "
   line[1] = "                           "
   line[2] = "                           "
   line[3] = "                           "
   line[4] = "                           "

def primitives(device, draw):
    # Draw a rectangle of the same size of screen
    draw.rectangle(device.bounding_box, outline="white")

for _ in range(2):
    with canvas(device) as draw:
        primitives(device, draw)

def OLED_WAIT_FOR_PTT():
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(10)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 5), "warte auf", font = oled_font, fill = "white")
       draw.text((5, 40), "       Click", font = oled_font, fill = "white")

def oled_TRAFFIC_LIGHT():
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(200)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 35), "AMPEL ROT", font = oled_font, fill = "white")

def oled_AWOS():
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(200)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 5), "transmit", font = oled_font, fill = "white")
       draw.text((5, 30), "AWOS  info", font = oled_font, fill = "white")

def oled_SO():
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(200)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 5), "SPECIAL", font = oled_font, fill = "white")
       draw.text((5, 30), " ORDER", font = oled_font, fill = "white")

def oled_SCROLL_VALUES(lines, job):
   # display last 5 values of PTT level
   oled_font = ImageFont.truetype('FreeSans.ttf', 10)
   with canvas(device) as draw:
      draw.rectangle(device.bounding_box, outline = "white", fill = "black")
      draw.text((3, 3), lines[4], font = oled_font, fill = "white")
      draw.text((3, 13), lines[3], font = oled_font, fill = "white")
      draw.text((3, 23), lines[2], font = oled_font, fill = "white")
      draw.text((3, 33), lines[1], font = oled_font, fill = "white")
      draw.text((3, 43), lines[0], font = oled_font, fill = "white")
      if len(job) > 0:
#         print("job =",job)
         draw.text((3, 53), job, font = oled_font, fill = "white")

def add_last_to_array(lines, lastvalue):
     # shift elements of the array by one position up and add lastvalue at pos 0
     for i in range(4,-1,-1):
        line[i] = line[i-1]
     line[0] = lastvalue
     return(lines)

def startup_screen():
    regulator = framerate_regulator(fps=10)
    img_path = str(Path(__file__).resolve().parent.parent.joinpath('media', 'snoopy-35.gif'))
    snoopy = Image.open(img_path)
    size = [min(*device.size)] * 2
    posn = ((device.width - size[0]) // 2, device.height - size[1])

    for frame in ImageSequence.Iterator(snoopy):
        with regulator:
            background = Image.new("RGB", device.size, "white")
            background.paste(frame.resize(size, resample=Image.LANCZOS), posn)
            device.display(background.convert(device.mode))


def brotzeit():
    regulator = framerate_regulator(fps=10)
    img_path = str(Path(__file__).resolve().parent.parent.joinpath('media', 'ww01.gif'))
    weisswurst  = Image.open(img_path)
    size = [min(*device.size)] * 2
    posn = ((device.width - size[0]) // 2, device.height - size[1])

    for frame in ImageSequence.Iterator(weisswurst):
        with regulator:
            background = Image.new("RGB", device.size, "white")
            background.paste(frame.resize(size, resample=Image.LANCZOS), posn)
            device.display(background.convert(device.mode))


def setup_IPC_queue():
   # setup Inter-Process-Communication:
   BaseManager.register('queue_master')
   BaseManager.register('queue_slave')
   m = BaseManager(address=('localhost', 50000), authkey=b'AWOS')
   m.connect()
   return(m)

m = setup_IPC_queue()

# inter-process-communication queue master to slave:
queue_master = m.queue_master()
# inter-process-communication queue slave to master (not used here):
queue_slave = m.queue_slave()

init_array()

while 1:
   msg = queue_master.get()
   msg = msg.split("_")
   key = msg[0]

   if key == "INIT":
      startup_screen()

   if key == "RED":
      oled_TRAFFIC_LIGHT()

   if key == "WAIT":
      init_array()
      OLED_WAIT_FOR_PTT()

   if key == "TX":
      oled_AWOS()

   if key == "CLEAR":
      init_array()
      device.clear()

   if key == "HIT":
      lastvalue = msg[1]
      line = add_last_to_array(line,lastvalue)
      oled_SCROLL_VALUES(line, "")

   if key == "PTT":
      val = msg[1]
      oled_SCROLL_VALUES(line, val)

   if key == "SO":
      oled_SO()
      time.sleep(1)
      brotzeit()

m.shutdown()
