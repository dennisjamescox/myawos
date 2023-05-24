################################################################################
# ecowitt_getweather.py   ecowitt api  
# by Dennis Cox and Johann Wiesheu, Dec. 2022 
# December 22 2022
# pull current weather from local Ecowitt weather station by API
# output is weather.txt, units imperial or metric, depending on the CMD-line args.
# time in zulu
# wind in degrees
# wind speed in knots
# altimeter in inch or hPa
# temp in Fahrenheit or (°C)
# dewpoint in Fahrenheit or (°C)
################################################################################


def main():
   import argparse
   import time
   import datetime
   import json
   import requests
   from gtts import gTTS
   import os
   
   HOME=os.environ['HOME']
   api_key_file = HOME + "/.weather_station_authentication/API_data.txt"

   
   # CMD line arguments
   p=argparse.ArgumentParser()
   p.add_argument('-unit', required=True, choices=['imperial', 'metric'], help='Required: Imperial or Metric units.')
   args = p.parse_args()
   unit = args.unit

   # USE ACTUAL API
   # doc.ecowitt.net/web/
   # read key from file API_data.txt:
   buf = [0]*3            # Array for api data
   apifile = open(api_key_file, 'r')
   data = apifile.readlines()
   for i in range(len(data)):
       buf[i] = data[i].strip()+ ' '
   application_key = buf[0]
   api_key = buf[1]
   mac = buf[2]
   apifile.close()

   url = "https://api.ecowitt.net/api/v3/device/real_time?" + application_key.strip() + "&" + api_key.strip() + "&" + mac.strip() + "&call_back=all"

#   print("URL:",url)

   r = requests.get(url)
   
   # Uncomment for debugging
   #print("raw data from ecowitt")
   #print(r.text)
   #print("---------------------------------------------------------------")
   #print("---------------------------------------------------------------")
   
   # USE SAMPLE FILE
   #r = open('/home/pilot/ecowitt/ecowitt_sample.json')
   
   results = json.loads(r.text)
   
   # Uncomment for debugging
   #print("parsed data from ecowitt:")
   #print(json.dumps(results, indent=4))
   
   zulutime = datetime.datetime.utcnow()
   
   # zulu time
   hours_minutes = zulutime.strftime("%H%M")
   hours = zulutime.strftime("%H")
   minutes = zulutime.strftime("%M")
   
   weatherfile = HOME+"/weather_station/ramdisk/weather.txt"

   weather = open(weatherfile, 'w')


   if unit == "metric":
      print("metric", file = weather)
   else:
      print("imperial", file = weather)
   
   # Time
  # print(f"{hours}", f"{minutes}", file = weather)
   print(f"{hours_minutes}", file = weather)
   
   
   # wind direction
   wind_direction = results['data']['wind']['wind_direction']['value']
   print(wind_direction, file = weather)
   
   
   # wind speed
   wind_speed = results['data']['wind']['wind_speed']['value']
   Fwind_speed = float(wind_speed)
   # converto to knots
   Fwind_speed = Fwind_speed * 0.87
   print(round(Fwind_speed), file = weather)
   
   # altimeter
   altimeter = results['data']['pressure']['relative']['value']

   if unit == "metric":       # convert to hPa
      Faltimeter = float(altimeter) / 0.029529980164712
      print(round(Faltimeter), file = weather)
   else:
      Faltimeter = float(altimeter)
      print( "{:.2f}".format(Faltimeter), file = weather)
   
   # outside temp
   outside_temp = results['data']['outdoor']['temperature']['value']
   Foutside_temp = float(outside_temp)
   if unit == "metric":       # convert to °C
      Foutside_temp = (Foutside_temp - 32) / 1.8
   print(round(Foutside_temp), file = weather)
   
   # dewpoint
   dewpoint = results['data']['outdoor']['dew_point']['value']
   Fdewpoint = float(dewpoint)
   if unit == "metric":       # convert to °C
      Fdewpoint = (Fdewpoint - 32) / 1.8
   print(round(Fdewpoint), file = weather)
   
   weather.close()
   
   # convert to mp3
   awos=HOME + "/weather_station/ramdisk/weather.mp3"


if __name__ == "__main__":
    main()

