import os
import wave
from myawos.audio import convert_weather_report_to_audio

AUDIO_FILE_NAMES = ["altimeter", "at", "dewpoint", \
                    "frenheight", "intro", "knot", \
                    "localtime", "point", "temp", \
                    "wind", "zulu"]

class MyAWOS:
    def __init__(self, backend, audio_path="audio/", clicks=5):
        self.backend = backend
        self.audio_path = audio_path
        self.clicks = clicks

    def _init_audio(self):
        dir_list = os.listdir(self.audio_path)
        # TODO raise exception if all files necessary are not found
        
        self.audio = {}
        # get all the data for each wav file
        for afn in AUDIO_FILE_NAMES + [str(i) for i range(10)]:
            with wave.open(f"{i}.wav", "rb") as w:
                self.audio[str(i)] = [w.getparams(), w.readframes(w.getnframes())]

        # alias . to point
        self.audio["."] = self.audio["point"]


    def start(self):
        # TODO start listening for clicks
        #   click will put the request on a queue (multithreaded)
        #   it should handle the exponential restarting

        self._init_audio()

        while True:
            # get click request off some queue
            break

            wx_report = self.backend.get_weather()
            if not wx_report:
                # could not get weather from backend!
                # TODO raise exception
                return
            
            convert_weather_report_to_audio(wx_report, self.audio)

            # transmit(wx_audio)

