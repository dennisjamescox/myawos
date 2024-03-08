import os
import wave
from myawos.weather import WeatherReport

def _wav_path_for_char(c):
    # i don't know if default raspberry pi python has match yet...
    if ord(c) < 0x30 or ord(c) > 0x39:
        return None
    return f"{c}.wav"

def _convert_string_to_audio(s, audio):
    out = []
    for char in s:
        if char not in audio_files:
            print("invalid char in string")
            return None
        out.append(audio[char])
    return out

def convert_weather_report_to_audio(wx_report: WeatherReport, audio): 
    # we need to get every value in the weather report and replace each number
    #  with a wav file

    out = []
    out.append(audio["intro"])
    out.append(_convert_string_to_audio(wx_report.time))
    out.append(audio["zulu"])
    out.append(audio["wind"])
    out.append(_convert_string_to_audio(wx_report.wind_direction))
    out.append(audio["at"])
    out.append(_convert_string_to_audio(wx_report.wind_spped))
    out.append(audio["knots"])
    out.append(audio["altimeter"])
    out.append(_convert_string_to_audio(wx_report.altimeter))
    out.append(audio["temperature"])
    out.append(_convert_string_to_audio(wx_report.temperature))
    out.append(audio["dewpoint"])
    out.append(_convert_string_to_audio(wx_report.dewpoint))

    # TODO make this a param
    with wave.open("foo.wav", "wb") as output:
        output.setparams(out[0][0])
        for i in range(len(out)):
            output.writeframes(out[i][1])

