import json
import time
import datetime
import requests

from myawos.weather import WeatherReport

class EcowittBackend():
    def __init__(self):
        pass

    def get_weather(self):
        resp = requests.get(f"https://api.ecowitt.net/api/v3/device/realtime?application_key={self.app_key}&api_key={self.api_key}&mac={self.mac}&call_back=all")

        if not resp.ok:
            # failed to get ecowitt data
            return None

        results = json.loads(resp.text)

        zulutime = datetime.datetime.utcnow()
        wind_direction = results["data"]["wind"]["wind_direction"]["value"]
        wind_speed = results["data"]["wind"]["wind_speed"]["value"]
        altimeter = results["data"]["pressure"]["absolute"]["value"]
        outside_temperature = results["data"]["outdoor"]["temperature"]["value"]
        dewpoint = results["data"]["outdoor"]["dew_point"]["value"]

        return WeatherReport(zulutime, wind_direction \
                             wind_speed, altimeter, \
                             outside_temperature, dewpoint)
