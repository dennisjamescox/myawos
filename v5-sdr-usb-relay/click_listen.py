#!/usr/bin/env python3
"""MyAWOS radio-click detector with Airspy and HackRF backends."""

from __future__ import annotations

import argparse
import glob
import logging
import math
import shutil
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
import yaml


DEFAULT_CONFIG = Path(__file__).with_name("config.yaml")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid configuration: {path}")
    return config


def make_logger(config: dict[str, Any]) -> logging.Logger:
    log_config = config.get("logging", {})
    log_dir = Path(log_config.get("directory", "/home/user/weather_station"))
    log_dir.mkdir(parents=True, exist_ok=True)
    prefix = log_config.get("filename_prefix", "sdr_click")
    log_path = log_dir / f"{time.strftime('%Y-%m-%d')}_{prefix}.log"

    logger = logging.getLogger("myawos.click")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(message)s")
    for handler in (logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class SampleSource:
    unit = ""

    def __init__(self, command: list[str], chunk_bytes: int):
        self.command = command
        self.chunk_bytes = chunk_bytes
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        executable = self.command[0]
        if shutil.which(executable) is None:
            raise RuntimeError(f"Required SDR command not found: {executable}")
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

    def read_level(self) -> float:
        if self.process is None or self.process.stdout is None:
            raise RuntimeError("SDR source is not running")
        data = self.process.stdout.read(self.chunk_bytes)
        if not data:
            code = self.process.poll()
            raise RuntimeError(f"SDR stream ended unexpectedly (exit code {code})")
        return self.measure(data)

    def measure(self, data: bytes) -> float:
        raise NotImplementedError

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)


class AirspySource(SampleSource):
    unit = "RMS"

    def measure(self, data: bytes) -> float:
        samples = np.frombuffer(data, dtype=np.int16)
        if not len(samples):
            return 0.0
        return float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))


class HackRFSource(SampleSource):
    """Measure narrowband power from interleaved signed 8-bit HackRF IQ."""

    unit = "dBFS"

    def __init__(
        self,
        command: list[str],
        sample_rate: int,
        tune_offset_hz: int,
        channel_rate_hz: int,
    ):
        self.sample_rate = sample_rate
        self.tune_offset_hz = tune_offset_hz
        self.decimation = max(1, round(sample_rate / channel_rate_hz))
        complex_per_chunk = self.decimation * 256
        super().__init__(command, complex_per_chunk * 2)

        indices = np.arange(complex_per_chunk, dtype=np.float32)
        phase = 2.0 * np.pi * tune_offset_hz * indices / sample_rate
        self.nco = np.exp(1j * phase).astype(np.complex64)

    def measure(self, data: bytes) -> float:
        raw = np.frombuffer(data, dtype=np.int8)
        pair_count = len(raw) // 2
        usable = (pair_count // self.decimation) * self.decimation
        if usable == 0:
            return -120.0

        iq = raw[: usable * 2].reshape(-1, 2).astype(np.float32)
        complex_iq = iq[:, 0] + 1j * iq[:, 1]
        nco = self.nco[:usable]

        # Support either IQ spectral orientation. The hardware is tuned away
        # from the desired carrier, keeping its center/DC spike out of-band.
        positive = (complex_iq * nco).reshape(-1, self.decimation).mean(axis=1)
        negative = (complex_iq * np.conj(nco)).reshape(-1, self.decimation).mean(axis=1)
        rms = max(
            float(np.sqrt(np.mean(np.abs(positive) ** 2))),
            float(np.sqrt(np.mean(np.abs(negative) ** 2))),
        )
        return 20.0 * math.log10(max(rms / 127.0, 1e-6))


def build_source(config: dict[str, Any]) -> SampleSource:
    radio = config["radio"]
    sdr = config["sdr"]
    device = str(sdr.get("device", "airspy")).lower()
    frequency_hz = round(float(radio["frequency_mhz"]) * 1_000_000)
    sample_rate = int(sdr["sample_rate"])

    if device == "airspy":
        command = ["airspy_rx", "-f", str(radio["frequency_mhz"]), "-a", str(sample_rate), "-r", "-"]
        return AirspySource(command, chunk_bytes=8192)

    if device != "hackrf":
        raise ValueError(f"Unsupported SDR device: {device}")

    offset = int(sdr.get("tune_offset_hz", 100_000))
    command = [
        "hackrf_transfer",
        "-r", "-",
        "-f", str(frequency_hz + offset),
        "-s", str(sample_rate),
        "-a", "1" if sdr.get("amp_enable", False) else "0",
        "-l", str(int(sdr.get("lna_gain_db", 16))),
        "-g", str(int(sdr.get("vga_gain_db", 16))),
        "-b", str(int(sdr.get("baseband_filter_hz", 1_750_000))),
    ]
    serial_number = str(sdr.get("serial", "")).strip()
    if serial_number:
        command.extend(["-d", serial_number])
    return HackRFSource(
        command,
        sample_rate=sample_rate,
        tune_offset_hz=offset,
        channel_rate_hz=int(sdr.get("channel_rate_hz", 20_000)),
    )


class RelativeThreshold:
    def __init__(self, calibration_seconds: float, chunks_per_second: float, on_margin: float, off_margin: float):
        self.samples_needed = max(5, round(calibration_seconds * chunks_per_second))
        self.initial: list[float] = []
        self.noise_floor: float | None = None
        self.on_margin = on_margin
        self.off_margin = off_margin

    def observe_calibration(self, level: float) -> bool:
        if self.noise_floor is not None:
            return True
        self.initial.append(level)
        if len(self.initial) >= self.samples_needed:
            self.noise_floor = float(np.median(self.initial))
            return True
        return False

    def thresholds(self) -> tuple[float, float]:
        if self.noise_floor is None:
            raise RuntimeError("Noise-floor calibration is incomplete")
        return self.noise_floor + self.on_margin, self.noise_floor + self.off_margin

    def update_noise(self, level: float) -> None:
        if self.noise_floor is not None and level < self.noise_floor + self.off_margin:
            self.noise_floor = 0.995 * self.noise_floor + 0.005 * level

    def reset(self) -> None:
        """Recalibrate after the SDR has switched from transmit back to receive."""
        self.initial.clear()
        self.noise_floor = None


def find_usb_relay_port(configured: str) -> str | None:
    if configured != "auto":
        return configured
    candidates = (
        sorted(glob.glob("/dev/serial/by-id/*"))
        + sorted(glob.glob("/dev/ttyUSB*"))
        + sorted(glob.glob("/dev/ttyACM*"))
    )
    return candidates[0] if candidates else None


class Transmitter:
    def __init__(self, config: dict[str, Any], logger: logging.Logger, monitor_only: bool):
        self.config = config
        self.logger = logger
        self.monitor_only = monitor_only or not bool(config.get("safety", {}).get("transmit_enabled", False))
        self.serial_connection = None

    def ptt(self, enabled: bool) -> None:
        ptt = self.config["ptt"]
        method = ptt["method"]
        if method == "scripts":
            key = "enable_script" if enabled else "disable_script"
            subprocess.run(["python3", ptt[key]], check=False)
            return
        if method == "usb_relay":
            import serial

            if self.serial_connection is None or not self.serial_connection.is_open:
                port = find_usb_relay_port(str(ptt.get("port", "auto")))
                if not port:
                    raise RuntimeError("USB relay port not found")
                self.serial_connection = serial.Serial(port, int(ptt.get("baud", 9600)), timeout=1)
                time.sleep(0.2)
            key = "on_command_hex" if enabled else "off_command_hex"
            self.serial_connection.write(bytes.fromhex(ptt[key]))
            self.serial_connection.flush()
            return
        raise RuntimeError(f"Unknown PTT method: {method}")

    def trigger(self, source: SampleSource) -> bool:
        """Transmit once and return whether the receive source was restarted."""
        if self.monitor_only:
            self.logger.info("TRIGGER detected (monitor-only; PTT/audio suppressed)")
            return False

        method = str(self.config.get("transmission", {}).get("method", "ptt_audio")).lower()
        if method == "hackrf":
            self.trigger_hackrf(source)
            return True
        if method != "ptt_audio":
            raise RuntimeError(f"Unknown transmission method: {method}")

        audio = self.config["audio"]
        started = time.monotonic()
        try:
            self.ptt(True)
            subprocess.run(
                ["aplay", audio["file"]],
                check=False,
                timeout=float(audio.get("timeout_seconds", 45)),
            )
        except subprocess.TimeoutExpired:
            self.logger.error("Audio timeout; forcing PTT off")
        finally:
            if time.monotonic() - started > float(audio.get("max_tx_seconds", 50)):
                self.logger.error("Maximum transmit time exceeded")
            try:
                self.ptt(False)
            except Exception as exc:
                self.logger.error("Failed to disable PTT: %s", exc)
        return False

    def trigger_hackrf(self, source: SampleSource) -> None:
        safety = self.config.get("safety", {})
        if not bool(safety.get("contained_rf_confirmed", False)):
            raise RuntimeError("HackRF TX blocked: contained_rf_confirmed is not enabled")

        audio = self.config["audio"]
        tx = self.config.get("transmission", {})
        sdr = self.config["sdr"]
        radio = self.config["radio"]
        command = [
            sys.executable,
            str(tx.get("script", Path(__file__).with_name("hackrf_transmit_once.py"))),
            "--audio", str(audio["file"]),
            "--frequency-mhz", str(radio["frequency_mhz"]),
            "--sample-rate", str(int(tx.get("sample_rate", 2_000_000))),
            "--serial", str(sdr.get("serial", "")),
            "--tx-gain", str(int(tx.get("tx_gain_db", 0))),
            "--modulation-index", str(float(tx.get("modulation_index", 0.75))),
            "--carrier-scale", str(float(tx.get("carrier_scale", 0.5))),
            "--max-seconds", str(float(audio.get("timeout_seconds", 45))),
            "--transmit",
            "--confirm-contained-rf",
        ]

        self.logger.info("Stopping HackRF receive stream for one contained transmission")
        source.stop()
        try:
            subprocess.run(
                command,
                check=True,
                timeout=float(audio.get("max_tx_seconds", 50)),
            )
            self.logger.info("One-shot HackRF transmission completed")
        except subprocess.TimeoutExpired:
            self.logger.error("HackRF transmission timeout; returning to receive mode")
        except subprocess.CalledProcessError as exc:
            self.logger.error("HackRF transmission failed with status %s", exc.returncode)
        finally:
            self.logger.info("Restarting HackRF receive stream")
            source.start()


def run(config: dict[str, Any], monitor_only: bool, duration: float | None, print_levels: bool) -> int:
    logger = make_logger(config)
    source = build_source(config)
    source.start()
    sdr = config["sdr"]
    radio = config["radio"]
    transmitter = Transmitter(config, logger, monitor_only)

    required_clicks = int(radio["required_clicks"])
    click_window = float(radio["click_window_seconds"])
    cooldown = float(radio["cooldown_seconds"])
    min_click_gap = float(sdr["min_click_gap_seconds"])
    min_quiet_time = float(sdr["min_quiet_time_seconds"])
    is_relative = str(sdr.get("threshold_mode", "absolute")).lower() == "relative"

    relative: RelativeThreshold | None = None
    if is_relative:
        chunks_per_second = int(sdr["sample_rate"]) * 2 / source.chunk_bytes
        relative = RelativeThreshold(
            float(sdr.get("calibration_seconds", 2.0)),
            chunks_per_second,
            float(sdr.get("threshold_on_db_above_noise", 10.0)),
            float(sdr.get("threshold_off_db_above_noise", 6.0)),
        )

    click_times: deque[float] = deque()
    carrier_active = False
    carrier_went_quiet_at = time.monotonic()
    last_click_time = 0.0
    last_trigger_time = 0.0
    started_at = time.monotonic()
    last_level_print = 0.0

    logger.info("Starting %s: %s", sdr["device"], " ".join(source.command))
    logger.info("Listening for %d clicks within %.1f seconds", required_clicks, click_window)

    try:
        while duration is None or time.monotonic() - started_at < duration:
            level = source.read_level()
            now = time.monotonic()

            if relative is not None and not relative.observe_calibration(level):
                continue
            if relative is not None:
                threshold_on, threshold_off = relative.thresholds()
            else:
                threshold_on = float(sdr["threshold_on"])
                threshold_off = float(sdr["threshold_off"])

            if print_levels and now - last_level_print >= 1.0:
                floor = f" noise={relative.noise_floor:.1f}" if relative and relative.noise_floor is not None else ""
                logger.info(
                    "level=%.1f %s%s on=%.1f off=%.1f carrier=%s",
                    level, source.unit, floor, threshold_on, threshold_off, carrier_active,
                )
                last_level_print = now

            if carrier_active:
                if level < threshold_off:
                    carrier_active = False
                    carrier_went_quiet_at = now
                continue

            if relative is not None:
                relative.update_noise(level)

            quiet_long_enough = now - carrier_went_quiet_at >= min_quiet_time
            click_gap_ok = now - last_click_time >= min_click_gap
            if level <= threshold_on or not quiet_long_enough or not click_gap_ok:
                continue

            carrier_active = True
            last_click_time = now
            click_times.append(now)
            while click_times and now - click_times[0] > click_window:
                click_times.popleft()
            logger.info("Click %d level=%.1f %s", len(click_times), level, source.unit)

            if len(click_times) >= required_clicks:
                click_times.clear()
                if now - last_trigger_time < cooldown:
                    logger.info("Trigger ignored; cooldown active")
                    continue
                last_trigger_time = now
                source_restarted = transmitter.trigger(source)
                if source_restarted:
                    if relative is not None:
                        relative.reset()
                    carrier_active = False
                    carrier_went_quiet_at = time.monotonic()
                    last_click_time = 0.0
                    logger.info("Receive mode restored; recalibrating noise floor")
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        source.stop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--monitor-only", action="store_true", help="Detect clicks but never key PTT or play audio")
    parser.add_argument("--duration", type=float, help="Stop after this many seconds")
    parser.add_argument("--print-levels", action="store_true", help="Print approximately one signal-level sample per second")
    args = parser.parse_args()
    return run(load_config(args.config), args.monitor_only, args.duration, args.print_levels)


if __name__ == "__main__":
    raise SystemExit(main())
