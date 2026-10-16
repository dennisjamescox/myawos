# Architecture and source flow

MyAWOS separates data acquisition, product generation, receive/click detection,
and radio transmission. A failed network weather fetch cannot partially replace
the last good station file, and a stale station timestamp cannot be presented as
current weather.

## Data flow

```text
WeatherLink Live ──> weather.py ──────────────> weather.txt
                                                  │
AWC GFA service ──> get_clouds_from_awc.py ──> clouds.json
                                                  │
                             ┌────────────────────┴───────────────────┐
                             │                                        │
             convert_weather_txt_to_wav.pl          convert_weather_txt_to_sms.pl
                             │                                        │
                         generate.sh                            current_sms.txt
                             │                                        │
                         current.wav ────────────────> awos_to_image.py
                             │                                        │
HackRF/Airspy ──> click_listen.py ──> USB relay + radio              PNG
                             │
                    optional radio captures
```

## Request flow

1. The SDR continuously measures the configured primary channel.
2. Relative thresholds are calculated after a short noise-floor calibration.
3. Five carrier transitions inside the configured window create one request.
4. A cooldown rejects immediate repeat requests.
5. With transmission enabled, SDR receive stops, the relay keys PTT, ALSA plays
   `current.wav`, the relay releases PTT, and receive restarts.
6. The accepted-request log supplies the daily usage list.

## Source layout

| Path | Responsibility |
| --- | --- |
| `config.yaml` | Public, safe example for station, radio, SDR, audio, capture, relay, and safety settings |
| `weather.py` | Direct local station fetch, validation, stale-data rejection, atomic `weather.txt` update |
| `get_clouds_from_awc.py` | AWC GFA retrieval, 30-minute rate limit, lock, and cache freshness |
| `convert_weather_txt_to_wav.pl` | Converts the snapshot into a shell playlist of recorded voice clips |
| `convert_weather_txt_to_sms.pl` | Produces the readable advisory used by the PNG and integrations |
| `generate.sh` | Generated command list that atomically creates the spoken WAV |
| `awos_to_image.py` | Renders the readable advisory into a PNG |
| `weather_loop.sh` | Locks and orchestrates one complete generation cycle |
| `click_listen.py` | SDR backends, noise calibration, click state machine, PTT, and playback |
| `radio_audio.py` | Optional live PCM socket and captured WAV/JSON metadata |
| `daily_weather_email.py` | Sunrise scheduling, health checks, camera/report attachment, request list, NBM guidance |
| `myawos-*.service`, `*.timer` | Example systemd deployment units |
| `tests/` | Regression tests for cloud caching, stale weather, scheduling, capture, and transmission behavior |

## Freshness and atomicity

The observation timestamp supplied by the station is authoritative. Successful
files inherit that timestamp. When a refresh fails, MyAWOS records the error and
does not touch the old weather file, allowing every downstream component to
reach the same stale/not-stale decision. Output files are generated under a
temporary name and moved into place to prevent readers from seeing partial data.

AWC data has separate freshness rules: at most one outbound attempt every 30
minutes, last-known-good reuse for a short configurable period, then omission.
AWC cloud layers are model estimates and never replace the on-field observation.
