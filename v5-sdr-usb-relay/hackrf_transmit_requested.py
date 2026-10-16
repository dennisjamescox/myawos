#!/usr/bin/env python3
"""Consume one systemd handoff request and perform one contained HackRF TX."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid configuration: {path}")
    return config


def request_path(config: dict[str, Any]) -> Path:
    return Path(
        config.get("transmission", {}).get(
            "request_file", f"/run/user/{os.getuid()}/myawos-hackrf-tx.request"
        )
    )


def build_command(config: dict[str, Any]) -> list[str]:
    radio = config["radio"]
    sdr = config["sdr"]
    audio = config["audio"]
    tx = config["transmission"]
    return [
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


def consume_and_transmit(config: dict[str, Any]) -> bool:
    marker = request_path(config)
    if not marker.exists():
        return False

    # Consume first: a failed or interrupted transmission must never repeat.
    marker.unlink()
    safety = config.get("safety", {})
    if not bool(safety.get("transmit_enabled", False)):
        print("TX request discarded: transmit_enabled is false", file=sys.stderr)
        return False
    if not bool(safety.get("contained_rf_confirmed", False)):
        print("TX request discarded: contained_rf_confirmed is false", file=sys.stderr)
        return False
    if str(config.get("transmission", {}).get("method", "")).lower() != "systemd_handoff":
        print("TX request discarded: transmission method is not systemd_handoff", file=sys.stderr)
        return False

    timeout = float(config["audio"].get("max_tx_seconds", 50))
    print("Consumed one-shot request after detector exit; starting contained TX", file=sys.stderr)
    try:
        subprocess.run(build_command(config), check=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("Requested HackRF TX timed out; request will not repeat", file=sys.stderr)
    except subprocess.CalledProcessError as exc:
        print(f"Requested HackRF TX failed with status {exc.returncode}; request will not repeat", file=sys.stderr)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    consume_and_transmit(load_config(args.config))
    # Always permit receive service recovery, even when TX failed.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
