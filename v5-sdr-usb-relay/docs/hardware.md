# Hardware and wiring

The current reference path uses separate receive and transmit hardware. The SDR
listens and detects clicks; the aviation radio performs the authorized AM voice
transmission. This keeps PTT and microphone behavior inside a purpose-built
radio.

## Reference components

- Always-on Linux computer (x86 Ubuntu or Raspberry Pi).
- Davis WeatherLink Live and compatible sensors.
- HackRF One/Pro or Airspy receiver.
- VHF airband receive antenna and feed line.
- Aviation handheld/base radio with an approved external microphone/PTT path.
- USB dry-contact relay.
- Radio-compatible audio interface/cable, with isolation or attenuation when
  required by the radio manual.

Vendor models, connectors, and accessory compatibility change. Confirm the
exact radio manual and pinout before ordering cables.

## Logical wiring

```text
weather sensors ──> WeatherLink Live ──LAN──> MyAWOS computer
airband antenna ──> SDR ──USB───────────────> MyAWOS computer
MyAWOS audio out ──isolation/level cable────> radio microphone input
MyAWOS computer ──USB relay COM/NO──────────> radio PTT and ground
radio antenna <────────────────────────────── aviation radio RF output
```

## Relay rule

The relay must behave like a switch closure only:

- Radio ground to relay **COM**.
- Radio PTT to relay **NO** (normally open).
- The USB side powers the relay electronics.
- Do not connect the relay's supply voltage to the radio microphone/PTT pins.

Use a continuity meter with everything disconnected to verify that COM–NO is
open at rest, closed only while commanded, and returns open after power loss or
program termination.

## RF and audio layout

Separate receive and transmit antennas sufficiently for the equipment and site,
use suitable coax/connectors, bond and ground outdoor installations correctly,
and protect the receiver from transmitter overload. Begin audio alignment at a
low level. Excess microphone drive creates distortion even when the received
signal strength is good.

Earlier MyAWOS releases used an Arduino or analog detector for clicks. Those
files remain in the repository as project history, but the current recommended
path is SDR detection plus a USB relay.
