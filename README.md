# MyAWOS

MyAWOS is an open-source, community-built weather information system for
private airports and airparks. It combines a local weather station, an SDR
receiver, an aviation radio, and a USB relay to provide an on-demand spoken
weather report after a configured click sequence.

The current implementation is in [`v5-sdr-usb-relay`](v5-sdr-usb-relay/).
It adds direct WeatherLink Live access, safely cached AWC estimated cloud
information, generated audio/text/PNG products, SDR click detection, radio PTT
through a USB relay, optional receive-audio capture, and a daily status email.

## Start here

- [Project website](https://dennisjamescox.github.io/myawos/)
- [Getting started](v5-sdr-usb-relay/docs/getting-started.md)
- [System architecture](v5-sdr-usb-relay/docs/architecture.md)
- [Hardware and wiring](v5-sdr-usb-relay/docs/hardware.md)
- [Configuration reference](v5-sdr-usb-relay/docs/configuration.md)
- [Operations and troubleshooting](v5-sdr-usb-relay/docs/operations.md)
- [Privacy and security](v5-sdr-usb-relay/docs/privacy-security.md)

New users who want the smallest supported installation should also consider
[MyAWOS Lite](https://dennisjamescox.github.io/myawos-lite/).

## Safety

MyAWOS is not an FAA-certified AWOS and is not a substitute for certified
weather sources, pilot judgment, or required airport equipment. Radio
installation and operation must comply with applicable rules and station
authorization. Public source defaults keep automatic transmission disabled.

Copyright © 2019–2026 Dennis Cox. See the repository history for additional
contributors and earlier hardware variants.
