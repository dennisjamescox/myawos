import time
import datetime
import weatherlink_live_local as wlll

class WeatherlinkBackend():
    def __init__(self):
        pass

    def get_weather(self):
        devices = wlll.discover()

        if len(devices) < 1:
            # failed to find devices
            return None

        device = devices[0].ip_addresses[0]
        conditions = wlll.get_conditions(device)

        zulutime = datetime.datetime.utcnow()
        # why did the dude make these properties so long??
        wind_direction = conditions.integrated_sensor_suites[0].wind_dir_at_hi_speed_last_10_min
        wind_speed = conditions.integrated_sensor_suites[0].wind_speed_hi_last_10_min
        altimeter = conditions.barometric.bar_sea_level
        temperature = conditions.integrated_sensor_suites[0].temp
        dewpoint = conditions.integrated_sensor_suites[0].dew_point

        return WeatherReport(zulutime, wind_direction, \
                             wind_speed, altimeter, \
                             outside_temperature, dewpoint)
