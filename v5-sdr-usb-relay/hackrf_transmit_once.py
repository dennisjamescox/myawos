#!/usr/bin/env python3
"""Generate or transmit one low-power AM MyAWOS broadcast with HackRF."""

from __future__ import annotations

import argparse
import subprocess
import sys
import wave
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

import numpy as np


def read_audio(path: Path, max_seconds: float | None = None) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        width = source.getsampwidth()
        sample_rate = source.getframerate()
        frames = source.getnframes()
        if max_seconds is not None:
            frames = min(frames, round(max_seconds * sample_rate))
        raw = source.readframes(frames)

    if channels != 1 or width != 1:
        raise ValueError("Expected mono, unsigned 8-bit PCM WAV audio")
    audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    if not len(audio):
        raise ValueError("Audio file is empty")
    audio -= float(audio.mean())
    peak = float(np.max(np.abs(audio)))
    if peak > 0:
        audio /= peak
    return audio, sample_rate


def iq_chunks(
    audio: np.ndarray,
    audio_rate: int,
    sample_rate: int,
    modulation_index: float,
    carrier_scale: float,
    audio_chunk_samples: int = 2048,
) -> Iterator[bytes]:
    if sample_rate % audio_rate:
        raise ValueError("HackRF sample rate must be an integer multiple of the audio rate")
    if not 0 < modulation_index <= 1:
        raise ValueError("Modulation index must be greater than zero and no more than one")
    if not 0 < carrier_scale <= 0.5:
        raise ValueError("Carrier scale must be greater than zero and no more than 0.5")

    ratio = sample_rate // audio_rate
    fractions = (np.arange(ratio, dtype=np.float32) / ratio)[None, :]
    for start in range(0, len(audio) - 1, audio_chunk_samples):
        end = min(start + audio_chunk_samples, len(audio) - 1)
        current = audio[start:end, None]
        following = audio[start + 1 : end + 1, None]
        interpolated = (current + (following - current) * fractions).reshape(-1)
        envelope = carrier_scale * (1.0 + modulation_index * interpolated)
        i_samples = np.rint(np.clip(envelope, 0.0, 1.0) * 127.0).astype(np.int8)
        iq = np.zeros(i_samples.size * 2, dtype=np.int8)
        iq[0::2] = i_samples
        yield iq.tobytes()


def stream_iq(chunks: Iterator[bytes], destination: BinaryIO) -> int:
    total = 0
    for chunk in chunks:
        destination.write(chunk)
        total += len(chunk)
    destination.flush()
    return total


def transmit(command: list[str], chunks: Iterator[bytes]) -> int:
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        total = stream_iq(chunks, process.stdin)
        process.stdin.close()
        result = process.wait()
    except BaseException:
        process.kill()
        process.wait()
        raise
    if result != 0:
        raise RuntimeError(f"hackrf_transfer exited with status {result}")
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, default=Path("/home/user/weather_station/current.wav"))
    parser.add_argument("--frequency-mhz", type=float, default=122.700)
    parser.add_argument("--sample-rate", type=int, default=2_000_000)
    parser.add_argument("--serial", default="", help="optional HackRF serial number")
    parser.add_argument("--tx-gain", type=int, default=0)
    parser.add_argument("--modulation-index", type=float, default=0.75)
    parser.add_argument("--carrier-scale", type=float, default=0.5)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--output-iq", type=Path, help="Write IQ to a file instead of transmitting")
    parser.add_argument("--transmit", action="store_true")
    parser.add_argument(
        "--confirm-contained-rf",
        action="store_true",
        help="Required for TX: confirms a dummy load, attenuated test path, or shielded enclosure is in use",
    )
    args = parser.parse_args()

    if args.transmit == bool(args.output_iq):
        parser.error("choose exactly one of --transmit or --output-iq")
    if args.transmit and not args.confirm_contained_rf:
        parser.error("--transmit requires --confirm-contained-rf")
    if not 0 <= args.tx_gain <= 47:
        parser.error("--tx-gain must be between 0 and 47 dB")

    audio, audio_rate = read_audio(args.audio, args.max_seconds)
    chunks = iq_chunks(audio, audio_rate, args.sample_rate, args.modulation_index, args.carrier_scale)
    duration = (len(audio) - 1) / audio_rate

    if args.output_iq:
        with args.output_iq.open("wb") as destination:
            total = stream_iq(chunks, destination)
        print(f"Generated {total} IQ bytes ({duration:.3f} seconds) at {args.sample_rate} samples/sec")
        return 0

    command = [
        "hackrf_transfer",
        "-t", "-",
        "-f", str(round(args.frequency_mhz * 1_000_000)),
        "-s", str(args.sample_rate),
        "-a", "0",
        "-x", str(args.tx_gain),
        "-b", "1750000",
    ]
    if args.serial:
        command.extend(["-d", args.serial])
    print(
        f"Transmitting once at {args.frequency_mhz:.6f} MHz for {duration:.2f} seconds, "
        f"RF amp off, TX gain {args.tx_gain} dB",
        file=sys.stderr,
    )
    total = transmit(command, chunks)
    print(f"Transmission complete ({total} IQ bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
