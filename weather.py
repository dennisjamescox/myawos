import weatherlink_live_local as wlll
import time
import datetime

devices = wlll.discover()
#print(devices)

# select first device, get IP address
ip_first_device = devices[0].ip_addresses[0]



# specify units
wlll.set_units(
    temperature=wlll.units.TemperatureUnit.CELSIUS,
    pressure=wlll.units.PressureUnit.INCH_MERCURY,
    rain=wlll.units.RainUnit.INCH,
    wind_speed=wlll.units.WindSpeedUnit.MILES_PER_HOUR,
)


# poll sensor data / conditions
#while True:
conditions = wlll.get_conditions(ip_first_device)
zulutime = datetime.datetime.utcnow()

# zulu time
hours_minutes = zulutime.strftime("%H%M")


weatherFile = open('/home/pi/weather_station/weather.txt', 'w')

print(f"{hours_minutes}", file = weatherFile)

# wind direction
wind_direction = conditions.integrated_sensor_suites[0].wind_dir_at_hi_speed_last_10_min
print(wind_direction, file = weatherFile)


# wind speed
wind_speed = conditions.integrated_sensor_suites[0].wind_speed_hi_last_10_min
print(f"{round(wind_speed)}", file = weatherFile)

# altimeter    
altimeter = conditions.barometric.bar_sea_level
print(f"{round(altimeter,2)}", file = weatherFile)

# outside temp    
temp_in_c = conditions.integrated_sensor_suites[0].temp
print(f"{round(temp_in_c)}", file = weatherFile)

# dewpoint
dew_point = conditions.integrated_sensor_suites[0].dew_point
print(f"{round(dew_point)}", file = weatherFile)



weatherFile.close()
