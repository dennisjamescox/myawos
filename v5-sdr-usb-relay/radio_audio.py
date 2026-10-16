#!/usr/bin/env python3
"""Capture squelched radio audio and optionally feed a local live listener."""

from __future__ import annotations

import json
import logging
import socket
import time
import wave
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any


class RadioAudioCapture:
    def __init__(
        self,
        config: dict[str, Any],
        sample_rate: int,
        frequency_mhz: str,
        logger: logging.Logger,
    ):
        self.config = config
        self.sample_rate = sample_rate
        self.frequency_mhz = frequency_mhz
        self.logger = logger
        self.enabled = bool(config.get("enabled", False)) and sample_rate > 0
        self.live_enabled = bool(config.get("live_enabled", True))
        self.capture_directory = Path(config.get("directory", "/home/user/weather_station/radio_captures"))
        self.live_socket = str(config.get("live_socket", "/run/user/1000/myawos-radio-audio.sock"))
        self.pre_roll_seconds = max(0.0, float(config.get("pre_roll_seconds", 0.35)))
        self.tail_seconds = max(0.0, float(config.get("tail_seconds", 0.35)))
        self.minimum_active_seconds = max(0.0, float(config.get("minimum_active_seconds", 0.65)))
        self.maximum_clip_seconds = max(1.0, float(config.get("maximum_clip_seconds", 90)))
        self.prebuffer: deque[bytes] = deque()
        self.prebuffer_samples = 0
        self.frames: list[bytes] = []
        self.recording_started: datetime | None = None
        self.recording_samples = 0
        self.active_samples = 0
        self.quiet_samples = 0
        self.recording_context: list[dict[str, Any]] = []
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) if self.enabled else None

    @property
    def recording(self) -> bool:
        return self.recording_started is not None

    @staticmethod
    def _sample_count(pcm: bytes) -> int:
        return len(pcm) // 2

    def _send_live(self, pcm: bytes, active: bool) -> None:
        if self.socket is None or not self.live_enabled:
            return
        payload = pcm if active else bytes(len(pcm))
        try:
            self.socket.sendto(payload, self.live_socket)
        except (FileNotFoundError, ConnectionRefusedError, OSError):
            pass

    def _remember_prebuffer(self, pcm: bytes) -> None:
        samples = self._sample_count(pcm)
        self.prebuffer.append(pcm)
        self.prebuffer_samples += samples
        maximum = round(self.pre_roll_seconds * self.sample_rate)
        while self.prebuffer and self.prebuffer_samples > maximum:
            removed = self.prebuffer.popleft()
            self.prebuffer_samples -= self._sample_count(removed)

    def _start_recording(self, context: list[dict[str, Any]] | None = None) -> None:
        pre_roll = self.prebuffer_samples / self.sample_rate
        self.recording_started = datetime.now().astimezone()
        if pre_roll:
            self.recording_started = self.recording_started.fromtimestamp(
                self.recording_started.timestamp() - pre_roll,
                self.recording_started.tzinfo,
            )
        self.frames = list(self.prebuffer)
        self.recording_samples = self.prebuffer_samples
        self.active_samples = 0
        self.quiet_samples = 0
        self.recording_context = [dict(item) for item in (context or [])]

    def ingest(
        self,
        pcm: bytes,
        active: bool,
        *,
        live_pcm: bytes | None = None,
        live_active: bool | None = None,
        recording_context: list[dict[str, Any]] | None = None,
    ) -> None:
        if not self.enabled or not pcm:
            return
        samples = self._sample_count(pcm)
        self._send_live(
            live_pcm if live_pcm is not None else pcm,
            live_active if live_active is not None else active,
        )

        if not self.recording:
            self._remember_prebuffer(pcm)
            if not active:
                return
            self._start_recording(recording_context)
            self.active_samples += samples
            return

        self.frames.append(pcm)
        self.recording_samples += samples
        if active:
            self.active_samples += samples
            self.quiet_samples = 0
        else:
            self.quiet_samples += samples

        if self.quiet_samples >= round(self.tail_seconds * self.sample_rate):
            self.finish()
        elif self.recording_samples >= round(self.maximum_clip_seconds * self.sample_rate):
            self.finish()

    def finish(self) -> Path | None:
        if not self.recording or self.recording_started is None:
            return None
        active_seconds = self.active_samples / self.sample_rate
        frames = self.frames
        started = self.recording_started
        recording_context = self.recording_context
        duration = self.recording_samples / self.sample_rate
        self.frames = []
        self.recording_started = None
        self.recording_samples = 0
        self.active_samples = 0
        self.quiet_samples = 0
        self.prebuffer.clear()
        self.prebuffer_samples = 0
        self.recording_context = []

        if active_seconds < self.minimum_active_seconds:
            return None

        day_directory = self.capture_directory / started.strftime("%Y-%m-%d")
        day_directory.mkdir(parents=True, exist_ok=True)
        stem = started.strftime("%Y%m%dT%H%M%S.%f")[:-3]
        wav_path = day_directory / f"{stem}_{self.frequency_mhz.replace('.', '')}.wav"
        with wave.open(str(wav_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self.sample_rate)
            output.writeframes(b"".join(frames))

        ended = started.fromtimestamp(started.timestamp() + duration, started.tzinfo)
        metadata = {
            "id": wav_path.stem,
            "started_at": started.isoformat(),
            "ended_at": ended.isoformat(),
            "duration_seconds": round(duration, 2),
            "active_seconds": round(active_seconds, 2),
            "sample_rate": self.sample_rate,
            "frequency_mhz": self.frequency_mhz,
            "audio_file": wav_path.name,
        }
        if recording_context:
            metadata["owned_aircraft_gate"] = recording_context
        wav_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        self.logger.info("Captured radio audio %.1fs: %s", duration, wav_path)
        return wav_path

    def close(self) -> None:
        self.finish()
        if self.socket is not None:
            self.socket.close()
