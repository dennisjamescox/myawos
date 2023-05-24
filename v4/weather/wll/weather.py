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


weatherFile = open('/home/pilot/weather_station/ramdisk/weather.txt', 'w')

print(f"{hours_minutes}", file = weatherFile)
# wind direction

print(f"{conditions.integrated_sensor_suites[0].wind_dir_at_hi_speed_last_10_min}", file = weatherFile)
# wind speed    
print(f"{conditions.integrated_sensor_suites[0].wind_speed_hi_last_10_min}", file = weatherFile)
# altimeter    
print(f"{conditions.barometric.bar_sea_level}", file = weatherFile)
# outside temp    
print(f"{conditions.integrated_sensor_suites[0].temp}", file = weatherFile)
# dewpoint
print(f"{conditions.integrated_sensor_suites[0].dew_point}", file = weatherFile)
#    time.sleep(60)


weatherFile.close()
