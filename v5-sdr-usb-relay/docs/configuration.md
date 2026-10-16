# Configuration reference

Copy `config.yaml` to an ignored local file and change the copy. The committed
example deliberately contains no real email address, aircraft, SDR serial,
credential, or routable station address.

## Main sections

| Section | Important values |
| --- | --- |
| `station` | Airport identifier and coordinates used for labeling and AWC lookup |
| `weather` | Source type, local WeatherLink host/port, and maximum observation age |
| `radio` | Primary frequency, optional live-monitor channels, click count/window, cooldown |
| `sdr` | Backend, optional serial, sample/tune rates, gain, calibration, relative thresholds |
| `audio` | Generated WAV, ALSA device, volume, PTT lead/tail, timeout limits |
| `audio_capture` | Disabled-by-default captures, storage, socket, clip timing, optional aircraft gate |
| `transmission` | `ptt_audio` for a connected radio; legacy contained-lab HackRF mode is optional |
| `ptt` | USB relay serial protocol/port or explicit scripts |
| `logging` | Directory and filename prefix |
| `safety` | Master transmit gate; false in public source |

## Receiver tuning

The primary channel must fall inside the sampled bandwidth around
`sdr.tune_frequency_mhz`. Center-frequency offset avoids the SDR's DC spike.
Gain that is too low misses clicks; gain that is too high raises the noise floor
and overloads nearby signals. Use `--print-levels` and tune gain before changing
relative thresholds.

## Owned-aircraft auxiliary capture

This feature is optional and disabled. When enabled, auxiliary-channel audio is
stored only while a configured aircraft is present in the recent local ADS-B
snapshot. Add registrations/ICAO hex values only to the private deployed config:

```yaml
audio_capture:
  owned_aircraft_auxiliary_capture:
    enabled: true
    aircraft:
      - registration: "N12345"
        icao_hex: "A12345"
```

The ADS-B proximity is a correlation aid, not proof that a specific aircraft
made a transmission. Captured metadata should preserve that distinction.

## Daily email configuration

`daily_weather_email.yaml` is separate because its deployment permissions and
credential path differ. Configure the airport, timezone, coordinates, camera,
weather files, health endpoints, sender/recipient, SMTP account, and nearest
NOAA NBM station. Store the SMTP password only in the configured mode-600 file.
