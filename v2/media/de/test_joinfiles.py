#with open("weather.mp3", "ab") as myfile, open("WeatherStation_1.mp3", "rb") as file2:
#    myfile.write(file2.read())

with open("weather.mp3", "ab") as myfile, open("WeatherStation_1.mp3", "rb") as file2:
    file3 = open("WeatherStation_2.mp3", "rb")
    text3 = file3.read()
    file4 = open("WeatherStation_3.mp3", "rb")
    text4 = file4.read()
    textZ = text4 + text3 + file2.read()
    myfile.write(textZ)
