# ecowitt api  
# by Dennis Cox and Johann Wiesheu, Dec. 2022 
# December 22 2022
# output is weather.txt ---
# time in zulu
# wind in degrees
# wind speed in knots
# altimeter in hPa
# temp (°C)
# dewpoint (°C)


def main():
   import time
   import datetime
   import json
   import requests
   from gtts import gTTS
   import os
   
   
   
   headers = {'Accept' : 'application/json'}
   
   # USE ACTUAL API
   # doc.ecowitt.net/web/
   r = requests.get("https://api.ecowitt.net/api/v3/device/real_time?application_key=APPL-KEY&api_key=API-KEY&mac=MAC-ADDRESS&call_back=all")
   
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
   hours = zulutime.strftime("%H")
   minutes = zulutime.strftime("%M")
   
   #weatherFile = open('/home/pi/weather_station/weather.txt', 'w')
   weather="/home/pi/weather_station/ramdisk/weather.txt"
   weatherFile = open(weather, 'w')
   
   #print("Strassham Wetter", f"{hours_minutes}", " Zulu", file = weatherFile)
   print("Strassham Wetter . ", f"{hours}", "Uhr", f"{minutes}", "Zulu", file = weatherFile)
   
   
   # wind direction
   wind_direction = results['data']['wind']['wind_direction']['value']
   print("Wind aus", printWord(str(wind_direction)), "Grad",file = weatherFile)
   
   
   # wind speed
   wind_speed = results['data']['wind']['wind_speed']['value']
   Fwind_speed = float(wind_speed)
   # converto to knots
   Fwind_speed = Fwind_speed * 0.87
#   print("Mit", f"{round(Fwind_speed)}", "Knoten", file = weatherFile)
   print("Mit", printWord(str(round(Fwind_speed))), "Knoten", file = weatherFile)
   
   # altimeter
   altimeter = results['data']['pressure']['relative']['value']
   # convert to hPa
   Faltimeter = float(altimeter) / 0.029529980164712
   #print("QNH", f"{round(Faltimeter)}", "hektoPascal", file = weatherFile)
   print("QNH . ", printWord(str(round(Faltimeter))), "hektoPascal", file = weatherFile)
   
   # outside temp
   outside_temp = results['data']['outdoor']['temperature']['value']
   Foutside_temp = float(outside_temp)
   # convert to °C
   Foutside_temp = (Foutside_temp - 32) / 1.8
   print("Temperatur", printWord(str(round(Foutside_temp))), "Grad", file = weatherFile)
   
   # dewpoint
   dewpoint = results['data']['outdoor']['dew_point']['value']
   Fdewpoint = float(dewpoint)
   # convert to °C
   Fdewpoint = (Fdewpoint - 32) / 1.8
   print("Taupunkt", printWord(str(round(Fdewpoint))), "Grad", file = weatherFile)
   
   weatherFile.close()
   
   # convert to mp3
   os.system("gtts-cli --lang de -f /home/pi/weather_station/ramdisk/weather.txt -o /home/pi/weather_station/ramdisk/weather.mp3")
   
   #r.close()


# Function to return the word of the corresponding digit
def printValue(digit):

	# Switch block to check for each digit c

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

