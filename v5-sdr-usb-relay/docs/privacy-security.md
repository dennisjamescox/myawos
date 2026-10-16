# Privacy and security

The public MyAWOS configuration is intentionally generic. A deployed system can
contain sensitive operational information even when the source code does not.

## Keep private

- SMTP/API passwords and tokens.
- Real sender/recipient email addresses when not meant for publication.
- Private aircraft lists and ICAO addresses.
- SDR serial numbers and hardware inventory.
- Internal IP addresses, hostnames, and remote-copy destinations.
- Radio recordings, logs, ADS-B snapshots, and generated reports that reveal
  activity or location.

Use ignored local configuration files, mode-600 credential files, and limited
service accounts. Never put a password directly in a systemd unit or Git-tracked
YAML file.

## Network exposure

WeatherLink Live, PiAware, and the local MyAWOS services should normally stay on
a trusted LAN. If a dashboard is exposed outside the LAN, put it behind TLS and
an explicit firewall/authentication policy; do not expose raw device endpoints.

## Radio safety controls

`safety.transmit_enabled` is false in source. Treat that as a deployment control,
not a substitute for legal authority, correct wiring, RF engineering, or an
operator's pre-service inspection. The optional HackRF transmit utility requires
a separate contained-RF confirmation and is not the recommended installed path.

## Capture notice

Audio and ADS-B retention rules differ by jurisdiction and intended use. Before
enabling capture or public playback, establish a policy for access, retention,
deletion, and notice appropriate to the installation.
