#! /usr/bin/python3
# -*- coding: utf-8 -*-
##########################################################################
#
#   click_oled096.py
#
#   Initiate and display messages 
#   on OLED 128 x 64 pixel display with SSD1306 driver
#
#   by Johann Wiesheu / av.wiesheu@bayern-mail.de / Jan. 2023
#
# VERSION HISTORY
# 28 Feb 2023: 
# removed IPC Communication and use function call for display output
# for usage out of messenger module which uses IPC now
# included functions get_device() and display_settings() 
# which were in demo_opts.py before
#
##########################################################################
import time
import datetime
#from demo_opts import get_device
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw, Image, ImageSequence
from array import*
from multiprocessing.managers import BaseManager
from pathlib import Path
from luma.core.sprite_system import framerate_regulator
import sys
import logging
from luma.core import cmdline, error

# logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s - %(message)s'
)
# ignore PIL debug messages
logging.getLogger('PIL').setLevel(logging.ERROR)


#serial = i2c(port=1, address=0x3C)
#device = ssd1106(serial)

#logfile = "/home/pilot/weather_station/ramdisk/oled.log"
#l = open(logfile, 'a')

N = 5                   # n values for scrolling
lines = [0]*N            # Array for scrolling

def init_array():
   lines[0] = "                           "
   lines[1] = "                           "
   lines[2] = "                           "
   lines[3] = "                           "
   lines[4] = "                           "

def display_settings(device, args):
    """
    Display a short summary of the settings.

    :rtype: str
    """
    iface = ''
    display_types = cmdline.get_display_types()
    if args.display not in display_types['emulator']:
        iface = f'Interface: {args.interface}\n'

    lib_name = cmdline.get_library_for_display_type(args.display)
    if lib_name is not None:
        lib_version = cmdline.get_library_version(lib_name)
    else:
        lib_name = lib_version = 'unknown'

    import luma.core
    version = f'luma.{lib_name} {lib_version} (luma.core {luma.core.__version__})'

    return f'Version: {version}\nDisplay: {args.display}\n{iface}Dimensions: {device.width} x {device.height}\n{"-" * 60}'


def get_device(actual_args=None):
    """
    Create device from command-line arguments and return it.
    """
    if actual_args is None:
        actual_args = sys.argv[1:]
    parser = cmdline.create_parser(description='luma.examples arguments')
    args = parser.parse_args(actual_args)

    if args.config:
        # load config from file
        config = cmdline.load_config(args.config)
        args = parser.parse_args(config + actual_args)

   # create device
    try:
       device = cmdline.create_device(args)
#       print("args=",args)
#       print(display_settings(device, args))
       return(device)

    except error.Error as e:
        parser.error(e)
        return None


def primitives(device, draw):
    # Draw a rectangle of the same size of screen
    draw.rectangle(device.bounding_box, outline="white")

def OLED_WAIT_FOR_PTT():
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(10)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 5), "warte auf", font = oled_font, fill = "white")
       draw.text((5, 40), "       Click", font = oled_font, fill = "white")

def OLED_WAIT_FOR_PTT_ANIMATED():
    regulator = framerate_regulator(fps=10)
    img_path = str(Path(__file__).resolve().parent.parent.joinpath('media/display', 'warteaufclick.gif'))
    radio = Image.open(img_path)
    size = [min(*device.size)] * 2
    posn = ((device.width - size[0]) // 2, device.height - size[1])

    for frame in ImageSequence.Iterator(radio):
        with regulator:
            background = Image.new("RGB", device.size, "black")
            background.paste(frame.resize(size, resample=Image.LANCZOS), posn)
            device.display(background.convert(device.mode))

def OLED_TRAFFIC_LIGHT():
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(200)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 35), "AMPEL ROT", font = oled_font, fill = "white")

def OLED_AWOS():
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(200)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 5), "transmit", font = oled_font, fill = "white")
       draw.text((5, 30), "AWOS  info", font = oled_font, fill = "white")

def OLED_SO():
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(200)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 5), "SPECIAL", font = oled_font, fill = "white")
       draw.text((5, 30), " ORDER", font = oled_font, fill = "white")

def OLED_SCROLL_VALUES(lines, job):

   # display last 5 values of PTT level
   for i in range(4,-1,-1):
      if lines[i] == 0:                # when "0", initate display string as space
         lines[i] = "                           "

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

def OLED_TEST(val):
   oled_font = ImageFont.truetype('FreeSans.ttf', 20)
   device.contrast(10)
   with canvas(device) as draw:
       draw.rectangle(device.bounding_box, outline = "white", fill = "black")
       draw.text((5, 10), val, font = oled_font, fill = "white")

def add_last_to_array(lines, lastvalue):
     # shift elements of the array by one position up and add lastvalue at pos 0
     buf = [0] * 5            # Array for scrolling
     for i in range(4,-1,-1): # initiate local array
        buf[i] = "                           "

     for i in range(4,-1,-1):
        buf[i] = lines[i-1]
     buf[0] = lastvalue
     return(buf)

def startup_screen():
    regulator = framerate_regulator(fps=10)
    img_path = str(Path(__file__).resolve().parent.parent.joinpath('media/display', 'snoopy-35.gif'))
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
    img_path = str(Path(__file__).resolve().parent.parent.joinpath('media/display', 'ww01.gif'))
    weisswurst  = Image.open(img_path)
    size = [min(*device.size)] * 2
    posn = ((device.width - size[0]) // 2, device.height - size[1])

    for frame in ImageSequence.Iterator(weisswurst):
        with regulator:
            background = Image.new("RGB", device.size, "black")
            background.paste(frame.resize(size, resample=Image.LANCZOS), posn)
            device.display(background.convert(device.mode))


init_array()
device = get_device()   # get parameters of installed OLED device

for _ in range(2):
    with canvas(device) as draw:
        primitives(device, draw)

def display_oled096(msg):
   global lines
   
   if msg.subject == "INIT":
      startup_screen()

   if msg.subject == "RED":
      OLED_TRAFFIC_LIGHT()

   if msg.subject == "WAIT":
      init_array()
      OLED_WAIT_FOR_PTT()

   if msg.subject == "WAIT_ANIMATED":
      init_array()
      OLED_WAIT_FOR_PTT_ANIMATED()

   if msg.subject == "TX":
      OLED_AWOS()

   if msg.subject == "CLEAR":
      init_array()
      device.clear()

   if msg.subject == "HIT":
      lastvalue = msg.text
      lines = add_last_to_array(lines,lastvalue)
      OLED_SCROLL_VALUES(lines, "")

   if msg.subject == "PTT":
      OLED_SCROLL_VALUES(lines, msg.text)

   if msg.subject == "SO":
      OLED_SO()
      time.sleep(1)
      brotzeit()

   if msg.subject == "TEST":
      OLED_TEST(msg.text)

