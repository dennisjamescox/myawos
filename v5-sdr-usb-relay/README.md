# MyAWOS v5 — SDR receiver and USB-relay radio transmitter

This directory contains the current full MyAWOS runtime. It produces a single
weather snapshot and uses that snapshot for the spoken WAV, text advisory, and
weather PNG. Five valid clicks on the configured primary frequency can key a
connected aviation radio and play the latest report.

## Current capabilities

- Direct local WeatherLink Live observations; the optional discovery library
  is no longer required.
- A hard 12-hour freshness cutoff. When observations are unavailable or stale,
  all products say **“No weather available at this time”** instead of reading
  old conditions.
- AWC GFA model-estimated cloud layers, clearly labeled **AWC Estimated**, with
  a 30-minute request limiter and last-known-good cache.
- HackRF or Airspy receive support with relative-noise click detection.
- USB-relay PTT and ALSA audio playback through a connected aviation radio.
- Configurable 85% default master playback level.
- Optional multi-frequency live monitoring and gated recording for aircraft
  configured by the operator.
- Daily HTML status/weather email scheduled for sunrise plus 10 minutes.
- No credentials, email addresses, aircraft, SDR serials, or private network
  destinations embedded in source defaults.

## Runtime flow

1. `weather.py` fetches the local station and atomically writes `weather.txt`.
2. `get_clouds_from_awc.py` refreshes or reuses `clouds.json`.
3. The Perl converters create `generate.sh` and `current_sms.txt`.
4. `generate.sh` atomically replaces `current.wav` from matching voice clips.
5. `awos_to_image.py` atomically replaces the text weather PNG.
6. `click_listen.py` detects the click sequence and, when explicitly enabled,
   controls the relay while `aplay` sends `current.wav` to the radio.

See the [architecture guide](docs/architecture.md) for the full data flow and
source layout.

## Quick start

```bash
cd v5-sdr-usb-relay
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.yaml config.local.yaml
```

Edit `config.local.yaml`, then validate receive-only operation:

```bash
python3 weather.py --config config.local.yaml --base "$PWD"
python3 click_listen.py --config config.local.yaml --monitor-only --print-levels
```

Do not enable transmission until the wiring, audio level, frequency,
authorization, and fail-safe PTT-off behavior have been checked. The complete
procedure is in [Getting started](docs/getting-started.md).

## Documentation

- [Getting started](docs/getting-started.md)
- [Architecture and source flow](docs/architecture.md)
- [Hardware and wiring](docs/hardware.md)
- [Configuration](docs/configuration.md)
- [Operations and troubleshooting](docs/operations.md)
- [Privacy and security](docs/privacy-security.md)

The generated example is available at
[`docs/rwj_awos-example.png`](docs/rwj_awos-example.png). Generated live WAV,
PNG, text, log, cache, database, and recording files are intentionally ignored
by Git.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile *.py
perl -c convert_weather_txt_to_wav.pl
perl -c convert_weather_txt_to_sms.pl
bash -n weather_loop.sh
```
