# ecowitt api ???? Taking a guess
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
#r = requests.get('https://api.ecowitt.net/api/v3/device/real_time?application_key=APPLICATION_KEY&api_key=API_KEY&mac=YOUR_MAC_CODE_OF_DEVICE&call_back=all', headers=headers)

# USE SAMPLE FILE
r = open('ecowitt_sample.json')

results = json.load(r)

# Uncomment for debugging
# print (json.dumps(results, indent=4))

zulutime = datetime.datetime.utcnow()

# zulu time
hours_minutes = zulutime.strftime("%H%M")


weatherFile = open('/home/pi/weather_station/weather.txt', 'w')

print(f"{hours_minutes}", file = weatherFile)

# wind direction
wind_direction = results['data']['wind']['wind_direction']['value']
print(wind_direction,file = weatherFile)


# wind speed
wind_speed = results['data']['wind']['wind_speed']['value']
Fwind_speed = float(wind_speed)
print(f"{round(Fwind_speed)}", file = weatherFile)

# altimeter
altimeter = results['data']['pressure']['absolute']['value']
print(altimeter, file = weatherFile)

# outside temp
outside_temp = results['data']['outdoor']['temperature']['value']
Foutside_temp = float(outside_temp)
print(f"{round(Foutside_temp)}", file = weatherFile)

# dewpoint
dewpoint = results['data']['outdoor']['dew_point']['value']
Fdewpoint = float(dewpoint)
print(f"{round(Fdewpoint)}", file = weatherFile)



weatherFile.close()

r.close()
