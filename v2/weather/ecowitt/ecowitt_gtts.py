################################################################################
# ecowitt_gtts.py
# Transcoding weather_gtts.txt (prepared for gTTS) to speech.
# by Johann Wiesheu 
# December 2022 
# output is weather.mp3, transcoded by Google Text To Speach gTTS online service
# Because the online service of Google is much slower than the local transcoding
# with language modules, this module is no longer maintained.
################################################################################

def main():
   import time
   import datetime
   from gtts import gTTS
   import os
   
   HOME=os.environ['HOME']
   
   # read key from file API_data.txt:
   buf = [0]*3            # Array for api data
   #apifile = open(api_key_file, 'r')
   #data = apifile.readlines()
   #for i in range(len(data)):
   #    buf[i] = data[i].strip()+ ' '
   #application_key = buf[0]
   #api_key = buf[1]
   #mac = buf[2]
   #apifile.close()

   lang = "en"

   gttsfile = HOME+"/weather_station/ramdisk/weather_gtts.txt"
   awos=HOME + "/weather_station/ramdisk/weather.mp3"

#  convert to mp3
#  convert it by CLI
#   os.system("gtts-cli --lang de -f $HOME/weather_station/ramdisk/weather.txt -o $HOME/weather_station/ramdisk/weather.mp3")

#  or better by Python library
   f = open( gttsfile, 'r')
   file_text = f.read()
   f.close()
 
   audio=gTTS(lang=lang, text=file_text)
   audio.save(awos)
   


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

