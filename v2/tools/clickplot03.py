import time
import statistics
from datetime import datetime

# Import the ADS1x15 module.
import Adafruit_ADS1x15


# Create an ADS1115 ADC (16-bit) instance at Address 0x48,Bus 1.
adc = Adafruit_ADS1x15.ADS1115(address=0x48, busnum=1)

# Choose a gain of 1 for reading voltages from 0 to 4.09V.
# Or pick a different gain to change the range of voltages that are read:
#  - 2/3 = +/-6.144V
#  -   1 = +/-4.096V
#  -   2 = +/-2.048V
#  -   4 = +/-1.024V
#  -   8 = +/-0.512V
#  -  16 = +/-0.256V
# See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
dU = 4.096 / 32767
GAIN = 1
Channel = 0
sample_no = 0
low_sample_no = 0
value = 0
TRIGGERLEVEL = 12000
max_mean = 0
adaptTRGlevel = 0
N = 10                # n values for median calculation
lastvalues = [0]*N
LOW1 = 0
LOW2 = 0
high_sample_no = 0
HIT_PLOT = 30000
HIT = 0
PEAK = 0
clickcount = 0
flushcount = 0

current_date = time.strftime("%G-%m-%d")
logfilename = current_date + "_adavalue.log"
logfilepath = "/home/pilot/weather_station/ramdisk/"
logfile = logfilepath + logfilename
print('Logfile = ', logfile)
l = open(logfile, 'w')

adc.start_adc(0,gain=GAIN)
print("#########################, Signal-Level Radio,###############", file = l)
print("current_time,", "sample_no,", "round(mean),", "round(PEAK),", "low_sample_no,","LOW1,", "high_sample_no,", "clickcount,", "HIT,", "round(max_mean),", "round(TRIGGERLEVEL)", "round(mean)V", file = l)

print('Reading ADS1x15 values, press Ctrl-C to quit...')
# Main loop.
while True:
    # Read all the ADC channel values in a list.
    #lastvalues[0] = adc.read_adc(Channel, gain=GAIN)
    lastvalues[0] = adc.get_last_result()
    sample_no +=1
    for i in range(N-1,-1,-1):
       lastvalues[i] = lastvalues[i-1]
#       print("lastvalues[", i, "] =", lastvalues[i])
    mean = statistics.mean(lastvalues)
    current_time = datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")
    print(f'{current_time}, {sample_no:05}, {round(mean):05}, {round(PEAK):05}, {low_sample_no}, {LOW1}, {high_sample_no}, {clickcount}, {HIT}, {round(max_mean):05}, {round(TRIGGERLEVEL):05}', "{:.3f}V".format(mean*dU),  file = l)

    flushcount +=1

    if mean < TRIGGERLEVEL:
       LOW1 = 1000
       low_sample_no += 1
#       current_time = datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")
#       print(current_time, "LOW recognized", file = l)
    if LOW1 == 1000:
       if mean > TRIGGERLEVEL:   # scanning for rising edge...
          high_sample_no += 1
          if mean > max_mean:
             max_mean = mean
          if adaptTRGlevel == 1:
             adaptTRGlevel = 0
             TRIGGERLEVEL = max_mean * 0.5 # !!!! Icom Handheld: absolute level of click falls click by click !!!!
          if lastvalues[0] > PEAK:
             PEAK = lastvalues[0]
#          current_time = datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")
#          print(current_time, "high_sample_no after LOW recognized", file = l)
#          print(f'{current_time}, {round(mean):06}, {sample_no:06}, {LOW1}, {high_sample_no}, {HIT}, {clickcount}',  file = l)
    if LOW1 and high_sample_no > 0:    # rising edge detected, scanning for falling edge...
          if mean < TRIGGERLEVEL:
             LOW2 = 2000
#             current_time = datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")
#             print(current_time, mean, "LOW2 recognized", file = l)
    if LOW1 and high_sample_no and LOW2:   # rising and falling edge recognized -> complete click
       clickcount +=1
       HIT = HIT_PLOT
       current_time = datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")
       print(f'{current_time}, {sample_no:05}, {round(mean):05}, {round(PEAK):05}, {low_sample_no}, {LOW1}, {high_sample_no}, {clickcount}, {HIT}, {round(max_mean):05}, {round(TRIGGERLEVEL):05}', "{:.3f}V".format(mean*dU),  file = l)
       l.flush()
       LOW1 = 0
       LOW2 = 0
       high_sample_no = 0
       HIT = 0
       PEAK = 0
       low_sample_no = 0
    #   sample_no = 0
       max_mean = 0
    if flushcount == 10:
       l.flush()
       flushcount = 0
       

    # Pause
    time.sleep(0.005)
