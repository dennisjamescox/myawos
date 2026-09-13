# MyAWOS v5: SDR, USB relay, and cloud integration

This version builds the spoken WAV, text advisory, and PNG from one weather
snapshot. `get_clouds_from_awc.py` caches AWC GFA model-derived cloud data in
`clouds.json`. It performs no more than one network attempt every 30 minutes,
even when scheduled runs overlap or an AWC request fails.

Cloud heights from this product are MSL. Outputs deliberately identify them as
"AWC Estimated clouds" so they are not confused with an on-field observed
ceiling.

## Runtime flow

1. `weather.py` writes the seven station observations to `weather.txt`.
2. `get_clouds_from_awc.py` refreshes or reuses `clouds.json`.
3. The two Perl converters generate `generate.sh` and `current_sms.txt`.
4. `generate.sh` atomically replaces `current.wav`.
5. `awos_to_image.py` atomically replaces the PNG from the same text advisory.

AWC failures use last-known-good cloud data for up to two hours. Older cloud
data is omitted. Set `MYAWOS_LAT`, `MYAWOS_LON`, or `MYAWOS_BASE` to override
the deployment defaults.

The additional fixed voice clips are in the repository `media` directory and
must be deployed with the other `WeatherStation_*.wav` files. Compound cloud
phrases are assembled from the matching-voice word and phrase recordings so
the vocabulary can be reused across GFA layer combinations.

An example of the generated cloud-enhanced image is available at
[`docs/rwj_awos-example.png`](docs/rwj_awos-example.png). The live, repeatedly
generated PNG and WAV outputs are intentionally ignored by Git.

## HackRF Pro click detection

`click_listen.py` supports `sdr.device: hackrf` and `sdr.device: airspy`. The
HackRF backend consumes signed 8-bit quadrature samples, offsets tuning away
from the center/DC spike, measures a narrow channel around the configured
frequency, and calibrates click thresholds relative to the local noise floor.

Start a manual receive-only calibration with:

```shell
python3 click_listen.py --monitor-only --print-levels
```

For contained lab testing only, `hackrf_transmit_once.py` generates conventional
AM IQ from `current.wav` and transmits it exactly once. It defaults to the lowest
HackRF TX gain with the RF amplifier disabled. RF transmission requires the
explicit `--confirm-contained-rf` flag.

The source configuration defaults both transmit safety gates to false. A
contained-lab deployment enables automatic transmission only when both
`safety.transmit_enabled` and `safety.contained_rf_confirmed` are true.
After five clicks within four seconds, the detector stops the half-duplex receive
stream, transmits `current.wav` once, restarts reception in a `finally` block,
and recalibrates the noise floor. A 30-second trigger cooldown remains active.
Set either safety gate to false, or start with `--monitor-only`, before removing
the dummy load, attenuated test path, or shielded enclosure.
