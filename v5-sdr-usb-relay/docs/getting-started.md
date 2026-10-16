# Getting started with full MyAWOS

Full MyAWOS is intended for an installed station where you control the weather
source, receive antenna, radio, audio interface, and PTT wiring. Build it in
stages: weather first, then receive-only click detection, then audio playback,
and finally PTT.

## 1. Before you begin

You need:

- An Ubuntu or Raspberry Pi OS computer that can remain on.
- A supported local weather source. The current reference configuration uses
  Davis WeatherLink Live.
- A HackRF or Airspy receiver and an antenna suitable for the monitored
  frequency.
- A legally operated aviation radio with external microphone/PTT access.
- A USB relay wired as a dry contact between the radio's PTT and ground.
- An isolated or radio-compatible audio connection from the computer output to
  the radio microphone input.

Start with a dummy load or otherwise controlled test setup. Confirm the radio's
manual, connector pinout, audio level requirements, and applicable radio rules.

## 2. Install system packages

On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip perl sox ffmpeg \
  alsa-utils hackrf libhackrf-dev
```

For an Airspy receiver, install the Airspy host tools supplied by your OS or
vendor. Package names vary by distribution.

## 3. Install MyAWOS

Clone the repository without needing a GitHub account:

```bash
git clone https://github.com/dennisjamescox/myawos.git
cd myawos/v5-sdr-usb-relay
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.yaml config.local.yaml
```

If Git is unavailable, download the repository ZIP from GitHub's **Code →
Download ZIP** menu and continue in the extracted `v5-sdr-usb-relay` folder.

## 4. Configure the station

Edit `config.local.yaml`:

1. Set `station.identifier`, `station.latitude`, and `station.longitude`.
2. Set `weather.host` to the WeatherLink Live address reserved in your router.
3. Confirm `radio.frequency_mhz` and the five-click timing.
4. Select `sdr.device`; leave `sdr.serial` blank when only one receiver exists.
5. Set the ALSA `audio.device` shown by `aplay -L`.
6. Leave `safety.transmit_enabled: false` during setup.

Never commit `config.local.yaml`, passwords, personal aircraft lists, recordings,
or generated station data to a public repository.

## 5. Test weather generation

```bash
python3 weather.py --config config.local.yaml --base "$PWD"
python3 get_clouds_from_awc.py --config config.local.yaml \
  --cache clouds.json --lock .clouds.lock
perl convert_weather_txt_to_wav.pl
perl convert_weather_txt_to_sms.pl
bash generate.sh
```

Inspect `weather.txt` and `current_sms.txt`, then play `current.wav` locally:

```bash
aplay current.wav
```

If the station observation is older than `weather.max_age_hours`, the report
must contain only the no-weather message. Fix the station connection or clock;
do not increase the limit merely to make stale data play.

## 6. Calibrate click detection without transmitting

Connect the SDR and run:

```bash
python3 click_listen.py --config config.local.yaml --monitor-only --print-levels
```

Confirm the receiver sees the correct channel, settles on a realistic noise
floor, and counts deliberate clicks while rejecting normal speech and noise.
Adjust gain and relative thresholds one change at a time.

## 7. Verify radio audio and PTT separately

With the transmitter connected to a dummy load or controlled test setup:

- Play `current.wav` through the selected ALSA device without keying the radio.
- Verify the level is clear and not distorted. Start below the configured 85%
  master level if the radio input is sensitive.
- Operate the USB relay manually and confirm PTT always releases.
- Confirm the relay uses the dry-contact COM and NO terminals; never feed relay
  supply voltage into the radio PTT line.

## 8. Enable the deployed service

Copy the runtime to a stable directory such as `/home/user/weather_station`,
keep its private configuration there, and adjust the service `User`, `Group`,
and paths for your account. Install the service only after the receive-only and
relay tests pass.

```bash
sudo cp myawos-click.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now myawos-click.service
sudo systemctl status myawos-click.service
```

As the last step, set `safety.transmit_enabled: true` in the deployed private
configuration. `contained_rf_confirmed` applies only to the optional HackRF
transmit path and must never be used to represent an antenna deployment.

## 9. Add the daily email

Copy `daily_weather_email.yaml` to a private local configuration, add the
station/email details, and store the SMTP application password in the specified
mode-600 password file. The timer wakes periodically; the program sends once
per local date when sunrise plus the configured offset has passed.

See [Operations](operations.md) for logging, failure checks, and recovery.
