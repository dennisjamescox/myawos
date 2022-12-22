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

# doc.ecowitt.net/web/
r = requests.get('https://api.ecowitt.net/api/v3/device/real_time?application_key=APPLICATION_KEY&api_key=API_KEY&mac=YOUR_MAC_CODE_OF_DEVICE&call_back=all', headers=headers)

results = json.loads(r)

zulutime = datetime.datetime.utcnow()

# zulu time
hours_minutes = zulutime.strftime("%H%M")


weatherFile = open('/home/pi/weather_station/weather.txt', 'w')

print(f"{hours_minutes}", file = weatherFile)

# wind direction
wind_direction = results["wind_direction"]
print(wind_direction,file = weatherFile)


# wind speed
print(results["wind_speed"], file = weatherFile)

# altimeter    
print(results["pressure"], file = weatherFile)

# outside temp    
print(results["temperature"], file = weatherFile)

# dewpoint
print(results["dew_point"], file = weatherFile)



weatherFile.close()
