#!/usr/bin/env python3
"""Read WeatherLink Live locally without requiring a discovery library."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

try:  # Optional convenience only; a configured/cached host is preferred.
    import weatherlink_live_local as wlll
except ImportError:
    wlll = None


MPH_TO_KT = 0.868976
CALM_KT_THRESHOLD = 1.0
DIR_ROUND_DEG = 10


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid configuration: {path}")
    return config


def write_error(path: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    path.write_text(f"{timestamp} {message}\n", encoding="utf-8")


def load_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return state if isinstance(state, dict) else {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def discover_ip_via_wlll() -> str | None:
    if wlll is None:
        return None
    try:
        devices = wlll.discover()
        return str(devices[0].ip_addresses[0]) if devices else None
    except Exception:
        return None


def http_get_current_conditions(host: str, port: int, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        f"http://{host}:{port}/v1/current_conditions",
        headers={"Accept": "application/json", "User-Agent": "MyAWOS/5"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Weather station returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8", errors="replace"))


def find_record(conditions: list[Any], data_structure_type: int, txid: int | None = None) -> dict[str, Any] | None:
    for record in conditions:
        if not isinstance(record, dict) or record.get("data_structure_type") != data_structure_type:
            continue
        if txid is not None and record.get("txid") != txid:
            continue
        return record
    return None


def normalize_dir_deg(value: float) -> int:
    return ((int(value) % 360) // DIR_ROUND_DEG * DIR_ROUND_DEG) % 360


def observation_values(
    payload: dict[str, Any], state: dict[str, Any], now: datetime | None = None
) -> tuple[list[str], datetime]:
    current_time = now or datetime.now(timezone.utc)
    data = payload.get("data") or {}
    conditions = data.get("conditions") or []
    if not isinstance(conditions, list) or not conditions:
        raise ValueError("response contained no conditions")

    outdoor = find_record(conditions, 1, txid=1) or find_record(conditions, 1)
    barometer = find_record(conditions, 3)
    if not outdoor or not barometer:
        raise ValueError("required sensor records are missing")

    try:
        observed_at = datetime.fromtimestamp(float(data["ts"]), timezone.utc)
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise ValueError("station observation timestamp is missing or invalid") from error
    if observed_at > current_time + timedelta(minutes=5):
        raise ValueError("station observation timestamp is in the future")

    try:
        wind_direction = float(outdoor["wind_dir_scalar_avg_last_1_min"])
        wind_speed_kt = float(outdoor["wind_speed_avg_last_1_min"]) * MPH_TO_KT
        wind_gust_kt = float(outdoor["wind_speed_hi_last_2_min"]) * MPH_TO_KT
        altimeter = float(barometer["bar_sea_level"])
        temperature_c = round((float(outdoor["temp"]) - 32.0) * 5.0 / 9.0)
        dewpoint_c = round((float(outdoor["dew_point"]) - 32.0) * 5.0 / 9.0)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("station weather values are missing or invalid") from error

    last_direction = state.get("last_wind_dir")
    if wind_speed_kt < CALM_KT_THRESHOLD and isinstance(last_direction, int):
        direction = last_direction
    else:
        direction = normalize_dir_deg(wind_direction)
        state["last_wind_dir"] = direction

    values = [
        observed_at.strftime("%H%M"),
        f"{direction:03d}",
        str(round(wind_speed_kt)),
        str(round(wind_gust_kt)),
        f"{altimeter:.2f}",
        str(temperature_c),
        str(dewpoint_c),
    ]
    return values, observed_at


def write_weather(path: Path, values: list[str], observed_at: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".weather.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as weather_file:
            weather_file.write("\n".join(values) + "\n")
        os.replace(temporary_name, path)
        timestamp = observed_at.timestamp()
        os.utime(path, (timestamp, timestamp))
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def refresh(config: dict[str, Any], base: Path) -> int:
    settings = config.get("weather", {})
    state_path = base / "weatherlink_state.json"
    error_path = base / "weather_error.txt"
    weather_path = base / "weather.txt"
    state = load_state(state_path)
    configured_host = str(os.environ.get("MYAWOS_WEATHERLINK_HOST", settings.get("host", ""))).strip()
    host = configured_host or str(state.get("ip", "")).strip() or discover_ip_via_wlll()
    if not host:
        write_error(error_path, "Weather unavailable: configure weather.host or MYAWOS_WEATHERLINK_HOST")
        return 1

    state["ip"] = host
    try:
        payload = http_get_current_conditions(
            host,
            int(settings.get("port", 80)),
            float(settings.get("timeout_seconds", 5)),
        )
        values, observed_at = observation_values(payload, state)
        write_weather(weather_path, values, observed_at)
        save_state(state_path, state)
        return 0
    except Exception as first_error:
        discovered = discover_ip_via_wlll() if not configured_host else None
        if discovered and discovered != host:
            try:
                payload = http_get_current_conditions(
                    discovered,
                    int(settings.get("port", 80)),
                    float(settings.get("timeout_seconds", 5)),
                )
                values, observed_at = observation_values(payload, state)
                state["ip"] = discovered
                write_weather(weather_path, values, observed_at)
                save_state(state_path, state)
                return 0
            except Exception as retry_error:
                first_error = retry_error
        write_error(error_path, f"Weather unavailable: {first_error}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yaml"))
    parser.add_argument("--base", type=Path, default=Path(os.environ.get("MYAWOS_BASE", "/home/user/weather_station")))
    args = parser.parse_args()
    return refresh(load_config(args.config), args.base)


if __name__ == "__main__":
    raise SystemExit(main())
