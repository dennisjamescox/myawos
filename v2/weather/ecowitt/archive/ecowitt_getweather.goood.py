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
   import time
   import datetime
   import json
   import requests
   from gtts import gTTS
   import os
   
   HOME=os.environ['HOME']
   api_key_file = HOME + "/.weather_station_authentication/API_data.txt"

   unit = "metric"
   
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
   # additional file only prepared for gTTS and German dialect (not longer maintained)
   gttsfile = HOME+"/weather_station/ramdisk/weather_gtts.txt"

   weather = open(weatherfile, 'w')
   gttsweather = open(gttsfile, 'w')


   if unit == "metric":
      print("metric", file = weather)
   else:
      print("imperial", file = weather)
   
   # Time
   print("Strassham Wetter . ", f"{hours}", "Uhr", f"{minutes}", "Zulu", file = gttsweather)
  # print(f"{hours}", f"{minutes}", file = weather)
   print(f"{hours_minutes}", file = weather)
   
   
   # wind direction
   wind_direction = results['data']['wind']['wind_direction']['value']
   print("Wind aus", printWord(str(wind_direction)), "Grad",file = gttsweather)
   print(wind_direction, file = weather)
   
   
   # wind speed
   wind_speed = results['data']['wind']['wind_speed']['value']
   Fwind_speed = float(wind_speed)
   # converto to knots
   Fwind_speed = Fwind_speed * 0.87
#   print("mit", f"{round(Fwind_speed)}", "Knoten", file = weatherFile)
   print("mit", printWord(str(round(Fwind_speed))), "Knoten", file = gttsweather)
   print(round(Fwind_speed), file = weather)
   
   # altimeter
   altimeter = results['data']['pressure']['relative']['value']
   if unit == "metric":       # convert to hPa
      Faltimeter = float(altimeter) / 0.029529980164712
   #print("QNH", f"{round(Faltimeter)}", "hektoPascal", file = weatherFile)
   print("QNH . ", printWord(str(round(Faltimeter))), "hektoPascal", file = gttsweather)
   print(round(Faltimeter), file = weather)
   
   # outside temp
   outside_temp = results['data']['outdoor']['temperature']['value']
   Foutside_temp = float(outside_temp)
   if unit == "metric":       # convert to °C
      Foutside_temp = (Foutside_temp - 32) / 1.8
   print("Temperatur", printWord(str(round(Foutside_temp))), "Grad", file = gttsweather)
   print(round(Foutside_temp), file = weather)
   
   # dewpoint
   dewpoint = results['data']['outdoor']['dew_point']['value']
   Fdewpoint = float(dewpoint)
   if unit == "metric":       # convert to °C
      Fdewpoint = (Fdewpoint - 32) / 1.8
   print("Taupunkt", printWord(str(round(Fdewpoint))), "Grad", file = gttsweather)
   print(round(Fdewpoint), file = weather)
   
   weather.close()
   gttsweather.close()
   
   # convert to mp3
   awos=HOME + "/weather_station/ramdisk/weather.mp3"

#  convert it by CLI
#   os.system("gtts-cli --lang de -f $HOME/weather_station/ramdisk/weather.txt -o $HOME/weather_station/ramdisk/weather.mp3")

#  or better by Python library
   f = open( gttsfile, 'r')
   file_text = f.read()
   f.close()
 
   audio=gTTS(lang='de', text=file_text)
   audio.save(awos)
   
   #r.close()


# Function to return the word of the corresponding digit
def printValue(digit):

	# Switch block to check for each digit c

	# For digit -
	if digit == '-':
		return(" minus")

	# For digit 0
	if digit == '0':
		return(" null")

	# For digit 1
	elif digit == '1':
		return(" eins")

	# For digit 2
	elif digit == '2':
		return(" zwo")

	#For digit 3
	elif digit=='3':
		return(" drei")

	# For digit 4
	elif digit == '4':
		return(" vier")

	# For digit 5
	elif digit == '5':
		return(" fünf")

	# For digit 6
	elif digit == '6':
		return(" sex")

	# For digit 7
	elif digit == '7':
		return(" sieben")

	# For digit 8
	elif digit == '8':
		return(" acht")

	# For digit 9
	elif digit == '9':
		return(" neun")

# Function to iterate through every
# digit in the given number
def printWord(N):
	i = 0
	length = len(N)
	digits = ""

	# Finding each digit of the number
	while i < length:
		
		# Print the digit in words
		digits = digits + printValue(N[i])
		i += 1
	return(digits)


if __name__ == "__main__":
    main()

