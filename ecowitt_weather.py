# ecowitt api
# dennisjcox@gmail.com
# av.wiesheu@bayern-mail.de
# December 22 2022
# output is weather.txt ---
# time in zulu
# wind in degrees
# wind speed in knots
# altimeter
# temp (c)
# dewpoint (c)

import time
import datetime
import json
import requests


headers = {'Accept' : 'application/json'}

# USE ACTUAL API
# doc.ecowitt.net/web/
r = requests.get("https://api.ecowitt.net/api/v3/device/real_time?application_key=XXXXXXXXXX&api_key=YYYYYYYYY&mac=ZZZZZZZZ&call_back=all")

# Uncomment for debugging
#print("raw data from ecowitt")
#print(r.text)
#print("---------------------------------------------------------------")
#print("---------------------------------------------------------------")

# USE SAMPLE FILE
#r = open('/home/pi/ecowitt/ecowitt_sample.json')

results = json.loads(r.text)

# Uncomment for debugging
#print("parsed data from ecowitt:")
#print(json.dumps(results, indent=4))

zulutime = datetime.datetime.utcnow()

# zulu time
hours_minutes = zulutime.strftime("%H%M")


#weatherFile = open('/home/pi/weather_station/weather.txt', 'w')
weatherFile = open('/home/pi/weather_station/ramdisk/weather.txt', 'w')

print(f"{hours_minutes}", file = weatherFile)

# wind direction
wind_direction = results['data']['wind']['wind_direction']['value']
print(wind_direction,file = weatherFile)


# wind speed
wind_speed = results['data']['wind']['wind_speed']['value']
Fwind_speed = float(wind_speed)
# converto to knots
Fwind_speed = Fwind_speed * 0.87
print(f"{round(Fwind_speed)}", file = weatherFile)

# altimeter
altimeter = results['data']['pressure']['absolute']['value']
# convert to hPa
Faltimeter = float(altimeter) / 0.029529980164712
print(f"{round(Faltimeter)}", file = weatherFile)

# outside temp
outside_temp = results['data']['outdoor']['temperature']['value']
Foutside_temp = float(outside_temp)
# convert to °C
Foutside_temp = (Foutside_temp - 32) / 1.8
print(f"{round(Foutside_temp)}", file = weatherFile)

# dewpoint
dewpoint = results['data']['outdoor']['dew_point']['value']
Fdewpoint = float(dewpoint)
# convert to °C
Fdewpoint = (Fdewpoint - 32) / 1.8
print(f"{round(Fdewpoint)}", file = weatherFile)



weatherFile.close()

r.close()
