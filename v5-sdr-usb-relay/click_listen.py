#!/usr/bin/env python3
"""MyAWOS radio-click detector with Airspy and HackRF backends."""

from __future__ import annotations

import argparse
import glob
import logging
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import deque
from contextlib import closing
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from radio_audio import RadioAudioCapture


DEFAULT_CONFIG = Path(__file__).with_name("config.yaml")


class TransmissionHandoff(Exception):
    """Tell systemd to transmit only after this detector has fully exited."""


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


def apply_master_volume(config: dict[str, Any], logger: logging.Logger) -> None:
    """Apply the configured ALSA Master volume without blocking the service."""
    audio = config.get("audio", {})
    configured_percent = audio.get("master_volume_percent")
    if configured_percent is None:
        return

    percent = int(configured_percent)
    if not 0 <= percent <= 100:
        raise ValueError("audio.master_volume_percent must be between 0 and 100")

    command = ["amixer"]
    device = str(audio.get("device", ""))
    card_match = re.search(r"(?:^|[:,])CARD=([^,]+)", device)
    if card_match:
        command.extend(["-c", card_match.group(1)])
    command.extend(["sset", "Master", f"{percent}%", "unmute"])

    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=5)
        logger.info("ALSA Master playback volume set to %d%%", percent)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        logger.warning("Could not set ALSA Master playback volume to %d%%: %s", percent, exc)


class SampleSource:
    unit = ""

    def __init__(self, command: list[str], chunk_bytes: int):
        self.command = command
        self.chunk_bytes = chunk_bytes
        self.process: subprocess.Popen[bytes] | None = None
        self.audio_sample_rate = 0
        self.last_audio_pcm = b""

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
        process = self.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        if process.stdout is not None:
            process.stdout.close()
        self.process = None


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
        channel_offsets_hz: dict[str, int] | None = None,
    ):
        self.sample_rate = sample_rate
        self.tune_offset_hz = tune_offset_hz
        self.decimation = max(1, round(sample_rate / channel_rate_hz))
        complex_per_chunk = self.decimation * 256
        super().__init__(command, complex_per_chunk * 2)
        self.audio_sample_rate = round(sample_rate / self.decimation)

        offsets = channel_offsets_hz or {"primary": tune_offset_hz}
        indices = np.arange(complex_per_chunk, dtype=np.float32)
        self.ncos = {
            name: np.exp(1j * (2.0 * np.pi * offset * indices / sample_rate)).astype(np.complex64)
            for name, offset in offsets.items()
        }
        self.primary_channel = next(iter(offsets))
        self.channel_levels: dict[str, float] = {}
        self.channel_audio_pcm: dict[str, bytes] = {}

    def _demodulate(self, complex_iq: np.ndarray, nco: np.ndarray) -> tuple[float, bytes]:
        selected = (complex_iq * nco[: len(complex_iq)]).reshape(-1, self.decimation).mean(axis=1)
        rms = float(np.sqrt(np.mean(np.abs(selected) ** 2)))
        envelope = np.abs(selected)
        carrier = max(float(np.mean(envelope)), 1e-3)
        audio = np.clip((envelope / carrier - 1.0) * 14000.0, -32768, 32767)
        level = 20.0 * math.log10(max(rms / 127.0, 1e-6))
        return level, audio.astype("<i2").tobytes()

    def measure(self, data: bytes) -> float:
        raw = np.frombuffer(data, dtype=np.int8)
        pair_count = len(raw) // 2
        usable = (pair_count // self.decimation) * self.decimation
        if usable == 0:
            return -120.0

        iq = raw[: usable * 2].reshape(-1, 2).astype(np.float32)
        complex_iq = iq[:, 0] + 1j * iq[:, 1]
        self.channel_levels = {}
        self.channel_audio_pcm = {}
        for name, nco in self.ncos.items():
            level, audio = self._demodulate(complex_iq, nco)
            self.channel_levels[name] = level
            self.channel_audio_pcm[name] = audio
        self.last_audio_pcm = self.channel_audio_pcm[self.primary_channel]
        return self.channel_levels[self.primary_channel]


def build_source(config: dict[str, Any]) -> SampleSource:
    radio = config["radio"]
    sdr = config["sdr"]
    device = str(sdr.get("device", "airspy")).lower()
    sample_rate = int(sdr["sample_rate"])

    if device == "airspy":
        command = ["airspy_rx", "-f", str(radio["frequency_mhz"]), "-a", str(sample_rate), "-r", "-"]
        return AirspySource(command, chunk_bytes=8192)

    if device != "hackrf":
        raise ValueError(f"Unsupported SDR device: {device}")

    live_frequencies = [str(value) for value in radio.get("live_monitor_frequencies_mhz", [])]
    primary_frequency = str(radio["frequency_mhz"])
    if primary_frequency not in live_frequencies:
        live_frequencies.insert(0, primary_frequency)
    tune_frequency_hz = round(
        float(sdr.get("tune_frequency_mhz", float(primary_frequency) + 0.1)) * 1_000_000
    )
    channel_offsets = {
        frequency: tune_frequency_hz - round(float(frequency) * 1_000_000)
        for frequency in live_frequencies
    }
    offset = channel_offsets[primary_frequency]
    command = [
        "hackrf_transfer",
        "-r", "-",
        "-f", str(tune_frequency_hz),
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
        channel_offsets_hz=channel_offsets,
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


class OwnedAircraftGate:
    """Keep auxiliary audio only while a configured aircraft is recently nearby."""

    def __init__(self, config: dict[str, Any], logger: logging.Logger):
        self.enabled = bool(config.get("enabled", False))
        self.database = Path(config.get("snapshot_database", ""))
        self.hex_codes = {
            str(item.get("icao_hex") or "").strip().upper(): str(item.get("registration") or "").strip().upper()
            for item in config.get("aircraft", [])
            if str(item.get("icao_hex") or "").strip()
        }
        self.max_age_seconds = max(5.0, float(config.get("max_age_seconds", 30)))
        self.max_distance_nm = max(0.1, float(config.get("max_distance_nm", 15)))
        self.check_interval_seconds = max(0.5, float(config.get("check_interval_seconds", 2)))
        self.logger = logger
        self.cached: list[dict[str, Any]] = []
        self.next_check_at = 0.0

    def nearby(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        if now < self.next_check_at:
            return self.cached
        self.next_check_at = now + self.check_interval_seconds
        if not self.enabled or not self.hex_codes or not self.database.is_file():
            self.cached = []
            return self.cached
        placeholders = ",".join("?" for _ in self.hex_codes)
        parameters: list[Any] = [time.time() - self.max_age_seconds, self.max_distance_nm, *self.hex_codes]
        try:
            with closing(sqlite3.connect(f"file:{self.database}?mode=ro", uri=True, timeout=1)) as connection:
                rows = connection.execute(
                    f"""SELECT UPPER(hex), MAX(registration), MIN(distance_nm),
                               CAST(AVG(altitude_ft) AS INTEGER)
                        FROM aircraft_samples
                        WHERE timestamp >= ? AND distance_nm <= ?
                          AND UPPER(hex) IN ({placeholders})
                        GROUP BY UPPER(hex)
                        ORDER BY MIN(distance_nm)""",
                    parameters,
                ).fetchall()
        except sqlite3.Error as exc:
            self.logger.warning("Owned-aircraft auxiliary capture gate unavailable: %s", exc)
            self.cached = []
            return self.cached
        self.cached = [
            {
                "hex": str(row[0]),
                "registration": str(row[1] or self.hex_codes.get(str(row[0]), "")),
                "callsign": str(row[1] or self.hex_codes.get(str(row[0]), row[0])),
                "distance_nm": round(float(row[2]), 1),
                "altitude_ft": int(row[3]),
                "match_basis": "owned-aircraft auxiliary capture gate",
            }
            for row in rows
        ]
        return self.cached


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
        if method == "systemd_handoff":
            safety = self.config.get("safety", {})
            if not bool(safety.get("contained_rf_confirmed", False)):
                raise RuntimeError("HackRF TX blocked: contained_rf_confirmed is not enabled")
            request_path = Path(
                self.config.get("transmission", {}).get(
                    "request_file", f"/run/user/{os.getuid()}/myawos-hackrf-tx.request"
                )
            )
            request_path.write_text(f"{time.time():.6f}\n", encoding="ascii")
            self.logger.info("One-shot TX handed off; detector exiting to release HackRF completely")
            raise TransmissionHandoff
        if method == "hackrf":
            self.trigger_hackrf(source)
            return True
        if method != "ptt_audio":
            raise RuntimeError(f"Unknown transmission method: {method}")

        audio = self.config["audio"]
        stop_receiver = bool(self.config.get("transmission", {}).get("stop_receiver_during_tx", True))
        receiver_stopped = False
        started = time.monotonic()
        try:
            if stop_receiver:
                self.logger.info("Stopping HackRF receive stream during radio transmission")
                source.stop()
                receiver_stopped = True
            self.ptt(True)
            lead_seconds = float(audio.get("ptt_lead_seconds", 0.5))
            if lead_seconds > 0:
                time.sleep(lead_seconds)
            command = ["aplay"]
            if audio.get("device"):
                command.extend(["-D", str(audio["device"])])
            command.append(str(audio["file"]))
            subprocess.run(
                command,
                check=True,
                timeout=float(audio.get("timeout_seconds", 45)),
            )
        except subprocess.TimeoutExpired:
            self.logger.error("Audio timeout; forcing PTT off")
        except subprocess.CalledProcessError as exc:
            self.logger.error("Audio playback failed with status %s", exc.returncode)
        finally:
            if time.monotonic() - started > float(audio.get("max_tx_seconds", 50)):
                self.logger.error("Maximum transmit time exceeded")
            try:
                tail_seconds = float(audio.get("ptt_tail_seconds", 0.3))
                if tail_seconds > 0:
                    time.sleep(tail_seconds)
                self.ptt(False)
            except Exception as exc:
                self.logger.error("Failed to disable PTT: %s", exc)
            if receiver_stopped:
                settle_seconds = float(
                    self.config.get("transmission", {}).get("receiver_settle_seconds", 0.5)
                )
                if settle_seconds > 0:
                    time.sleep(settle_seconds)
                self.logger.info("Restarting HackRF receive stream")
                source.start()
        return receiver_stopped

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
            "--tx-gain", str(int(tx.get("tx_gain_db", 0))),
            "--modulation-index", str(float(tx.get("modulation_index", 0.75))),
            "--carrier-scale", str(float(tx.get("carrier_scale", 0.5))),
            "--max-seconds", str(float(audio.get("timeout_seconds", 45))),
            "--transmit",
            "--confirm-contained-rf",
        ]
        if sdr.get("serial"):
            command.extend(["--serial", str(sdr["serial"])])

        self.logger.info("Stopping HackRF receive stream for one contained transmission")
        source.stop()
        try:
            settle_seconds = float(tx.get("device_settle_seconds", 1.0))
            if settle_seconds > 0:
                self.logger.info("Waiting %.1f seconds for HackRF TX mode change", settle_seconds)
                time.sleep(settle_seconds)
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
            settle_seconds = float(tx.get("device_settle_seconds", 1.0))
            if settle_seconds > 0:
                self.logger.info("Waiting %.1f seconds for HackRF RX mode change", settle_seconds)
                time.sleep(settle_seconds)
            self.logger.info("Restarting HackRF receive stream")
            source.start()


def run(config: dict[str, Any], monitor_only: bool, duration: float | None, print_levels: bool) -> int:
    logger = make_logger(config)
    apply_master_volume(config, logger)
    source = build_source(config)
    source.start()
    sdr = config["sdr"]
    radio = config["radio"]
    transmitter = Transmitter(config, logger, monitor_only)
    capture_config = config.get("audio_capture", {})
    audio_capture = RadioAudioCapture(
        capture_config,
        source.audio_sample_rate,
        str(radio["frequency_mhz"]),
        logger,
    )
    if config.get("audio_capture", {}).get("enabled", False) and not audio_capture.enabled:
        logger.warning("Radio audio capture is unavailable for the selected SDR source")

    auxiliary_gate_config = capture_config.get("owned_aircraft_auxiliary_capture", {})
    owned_aircraft_gate = OwnedAircraftGate(auxiliary_gate_config, logger)
    auxiliary_recorders: dict[str, RadioAudioCapture] = {}
    if owned_aircraft_gate.enabled and isinstance(source, HackRFSource):
        auxiliary_recorder_config = dict(capture_config)
        auxiliary_recorder_config["live_enabled"] = False
        for frequency in auxiliary_gate_config.get("frequencies_mhz", []):
            frequency = str(frequency)
            if frequency == str(radio["frequency_mhz"]) or frequency not in source.channel_audio_pcm and frequency not in source.ncos:
                continue
            auxiliary_recorders[frequency] = RadioAudioCapture(
                auxiliary_recorder_config,
                source.audio_sample_rate,
                frequency,
                logger,
            )

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

    live_frequencies = [str(value) for value in radio.get("live_monitor_frequencies_mhz", [])]
    primary_frequency = str(radio["frequency_mhz"])
    if primary_frequency not in live_frequencies:
        live_frequencies.insert(0, primary_frequency)
    auxiliary_relatives: dict[str, RelativeThreshold] = {}
    auxiliary_active: dict[str, bool] = {}
    if relative is not None and isinstance(source, HackRFSource):
        chunks_per_second = int(sdr["sample_rate"]) * 2 / source.chunk_bytes
        for frequency in live_frequencies:
            if frequency == primary_frequency:
                continue
            auxiliary_relatives[frequency] = RelativeThreshold(
                float(sdr.get("calibration_seconds", 2.0)),
                chunks_per_second,
                float(sdr.get("threshold_on_db_above_noise", 10.0)),
                float(sdr.get("threshold_off_db_above_noise", 6.0)),
            )
            auxiliary_active[frequency] = False

    click_times: deque[float] = deque()
    carrier_active = False
    carrier_went_quiet_at = time.monotonic()
    last_click_time = 0.0
    last_trigger_time = 0.0
    started_at = time.monotonic()
    last_level_print = 0.0

    logger.info("Starting %s: %s", sdr["device"], " ".join(source.command))
    logger.info("Listening for %d clicks within %.1f seconds", required_clicks, click_window)
    if len(live_frequencies) > 1:
        logger.info("Live audio priority scan: %s", " > ".join(live_frequencies))

    try:
        while duration is None or time.monotonic() - started_at < duration:
            level = source.read_level()
            now = time.monotonic()

            if isinstance(source, HackRFSource):
                for frequency, channel_relative in auxiliary_relatives.items():
                    channel_level = source.channel_levels.get(frequency, -120.0)
                    if not channel_relative.observe_calibration(channel_level):
                        continue
                    channel_on, channel_off = channel_relative.thresholds()
                    if auxiliary_active[frequency]:
                        if channel_level < channel_off:
                            auxiliary_active[frequency] = False
                    else:
                        channel_relative.update_noise(channel_level)
                        if channel_level > channel_on:
                            auxiliary_active[frequency] = True

            if relative is not None and not relative.observe_calibration(level):
                audio_capture.ingest(source.last_audio_pcm, False)
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

            trigger_requested = False
            if carrier_active:
                if level < threshold_off:
                    carrier_active = False
                    carrier_went_quiet_at = now
            else:
                if relative is not None:
                    relative.update_noise(level)

                quiet_long_enough = now - carrier_went_quiet_at >= min_quiet_time
                click_gap_ok = now - last_click_time >= min_click_gap
                if level > threshold_on and quiet_long_enough and click_gap_ok:
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
                        else:
                            last_trigger_time = now
                            trigger_requested = True

            live_pcm = source.last_audio_pcm
            live_active = carrier_active
            if not live_active and isinstance(source, HackRFSource):
                for frequency in live_frequencies:
                    if frequency == primary_frequency or not auxiliary_active.get(frequency, False):
                        continue
                    live_pcm = source.channel_audio_pcm.get(frequency, live_pcm)
                    live_active = True
                    break
            audio_capture.ingest(
                source.last_audio_pcm,
                carrier_active,
                live_pcm=live_pcm,
                live_active=live_active,
            )
            gate_matches = (
                owned_aircraft_gate.nearby()
                if any(auxiliary_active.get(frequency, False) or recorder.recording for frequency, recorder in auxiliary_recorders.items())
                else []
            )
            for frequency, recorder in auxiliary_recorders.items():
                recorder.ingest(
                    source.channel_audio_pcm.get(frequency, b""),
                    auxiliary_active.get(frequency, False) and bool(gate_matches),
                    recording_context=gate_matches,
                )

            if trigger_requested:
                logger.info("Weather request accepted")
                source_restarted = transmitter.trigger(source)
                if source_restarted:
                    if relative is not None:
                        relative.reset()
                    for channel_relative in auxiliary_relatives.values():
                        channel_relative.reset()
                    for frequency in auxiliary_active:
                        auxiliary_active[frequency] = False
                    carrier_active = False
                    carrier_went_quiet_at = time.monotonic()
                    last_click_time = 0.0
                    logger.info("Receive mode restored; recalibrating noise floor")
    except TransmissionHandoff:
        logger.info("Closing detector for systemd TX handoff")
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        audio_capture.close()
        for recorder in auxiliary_recorders.values():
            recorder.close()
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
