# Operations and troubleshooting

## Routine checks

```bash
systemctl status myawos-click.service
journalctl -u myawos-click.service --since today
hackrf_info
aplay -L
```

Check that station timestamps advance, `current_sms.txt` and `current.wav` agree,
the relay releases after every test, and the daily health report shows the
weather station, camera, and PiAware status expected for the deployment.

## Common symptoms

### “No weather available at this time”

Verify the WeatherLink host, LAN reachability, system clock, and the timestamp
in the station response. MyAWOS intentionally refuses to speak data older than
the configured limit. A failed fetch preserves the old source file for diagnosis
but downstream output remains the no-weather message.

### Clicks appear but no radio audio is heard

Check the accepted-request log, transmit safety gate, relay port/protocol, PTT
closure, ALSA device, computer mixer, cable pinout, microphone attenuation, and
radio frequency. Test playback and relay closure separately before testing the
complete path.

### False or missed clicks

Run receive-only with `--print-levels`. Confirm frequency and tune bandwidth,
then adjust SDR gain. Only after the noise floor is stable should you alter
`threshold_on_db_above_noise`, `threshold_off_db_above_noise`, minimum quiet
time, or minimum click gap.

### AWC clouds do not update

The fetcher intentionally permits only one network attempt per 30 minutes. Look
at the cache and lock paths, station coordinates, system time, and network DNS.
Expired AWC data is omitted rather than reported indefinitely.

## Safe recovery

Set `safety.transmit_enabled: false` before hardware work. Stop the service,
verify PTT is released electrically, make the change, validate receive-only,
then re-enable transmission as a deliberate final step.

## Backups

Back up private configuration, recorded voice media, and any captures or logs
you intend to retain. Do not rely on Git for generated data or secrets. Keep a
written record of radio/cable pinouts and known-good audio/SDR settings for the
specific installation.
