#!/usr/bin/env python3
"""Fetch and cache model-derived GFA cloud layers for MyAWOS."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml


DEFAULT_BASE = Path(os.environ.get("MYAWOS_BASE", "/home/user/weather_station"))
DEFAULT_CACHE = DEFAULT_BASE / "clouds.json"
DEFAULT_LOCK = DEFAULT_BASE / ".clouds.lock"
DEFAULT_LAT = float(os.environ.get("MYAWOS_LAT", "29.7618236"))
DEFAULT_LON = float(os.environ.get("MYAWOS_LON", "-94.8484264"))
MIN_FETCH_INTERVAL_SECONDS = 30 * 60
MAX_STALE_AGE_SECONDS = 2 * 60 * 60

HEADERS = {
    "User-Agent": "MyAWOS/1.0 (model-derived cloud display)",
    "Referer": "https://aviationweather.gov/gfa/",
}

CLOUD_COVER = {
    "SKC": "Clear",
    "CLR": "Clear",
    "FEW": "Few clouds",
    "SCT": "Scattered",
    "BKN": "Broken",
    "OVC": "Overcast",
    "VV": "Vertical visibility",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_cloud_layers(raw: str) -> list[dict[str, object]]:
    layers: list[dict[str, object]] = []
    for part in (item.strip() for item in (raw or "").split("/")):
        if not part:
            continue

        match = re.fullmatch(r"(SKC|CLR|FEW|SCT|BKN|OVC|VV)(\d{3})?", part)
        if match:
            code, altitude = match.groups()
            layer: dict[str, object] = {
                "kind": "layer",
                "code": code,
                "description": CLOUD_COVER[code],
            }
            if altitude:
                layer["base_msl_ft"] = int(altitude) * 100
            layers.append(layer)
            continue

        match = re.fullmatch(r"TOP (?:FL)?(\d{3})", part)
        if match:
            layers.append({"kind": "top", "top_msl_ft": int(match.group(1)) * 100})
            continue

        normalized = part.upper()
        if normalized in {"CI", "CIRRUS", "CI ABV", "CIRRUS ABV"}:
            layers.append({
                "kind": "cirrus",
                "above_fl180": normalized in {"CI ABV", "CIRRUS ABV"},
            })
            continue

        layers.append({"kind": "unknown", "raw": part})

    return layers


def spoken_text(layers: list[dict[str, object]]) -> str:
    phrases: list[str] = []
    for layer in layers:
        kind = layer.get("kind")
        if kind == "layer":
            phrase = str(layer["description"])
            if "base_msl_ft" in layer:
                phrase += f" at {int(layer['base_msl_ft']):,} feet MSL"
            phrases.append(phrase)
        elif kind == "top":
            phrases.append(f"Tops at {int(layer['top_msl_ft']):,} feet MSL")
        elif kind == "cirrus":
            phrase = "Cirrus clouds"
            if layer.get("above_fl180"):
                phrase += " above flight level one eight zero"
            phrases.append(phrase)

    if not phrases:
        return ""
    return "AWC Estimated clouds: " + ". ".join(phrases) + "."


def load_cache(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def timestamp_age_seconds(cache: dict[str, object], key: str) -> float | None:
    try:
        fetched = datetime.fromisoformat(str(cache[key]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return None
    return max(0.0, (utc_now() - fetched).total_seconds())


def write_json_atomic(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def fetch_clouds(lat: float, lon: float) -> dict[str, object]:
    now = utc_now()
    response = requests.get(
        "https://aviationweather.gov/api/info/gfa",
        params={"date": int(now.timestamp())},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    info = response.json()
    dref, tref = info["datim"].split("_")

    delta = 0.05
    response = requests.get(
        "https://aviationweather.gov/api/data/cldlayer",
        params={
            "wrap": "true",
            "zoom": 11,
            "model": "gfaak",
            "level": "sfc",
            "density": 0,
            "bbox": f"{lat-delta},{lon-delta},{lat+delta},{lon+delta}",
            "dref": dref,
            "tref": tref,
            "fhr": "00",
        },
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    features = response.json().get("features") or []

    if features:
        def distance(feature: dict[str, object]) -> float:
            lon2, lat2 = feature["geometry"]["coordinates"]  # type: ignore[index]
            return (float(lat2) - lat) ** 2 + (float(lon2) - lon) ** 2

        closest = min(features, key=distance)
        raw = str(closest.get("properties", {}).get("cldlayers", ""))
        point = closest["geometry"]["coordinates"]
    else:
        raw = ""
        point = None

    layers = parse_cloud_layers(raw)
    return {
        "fetched_at": now.isoformat().replace("+00:00", "Z"),
        "last_attempt_at": now.isoformat().replace("+00:00", "Z"),
        "source": "AWC GFA model-derived cloud grid",
        "source_cycle": f"{dref}_{tref}",
        "forecast_hour": "00",
        "requested_point": {"lat": lat, "lon": lon},
        "grid_point": point,
        "raw": raw,
        "layers": layers,
        "text": spoken_text(layers),
    }


def refresh(cache_path: Path, lock_path: Path, lat: float, lon: float) -> dict[str, object]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle, fcntl.LOCK_EX)
        cached = load_cache(cache_path)
        # Re-decode cached raw data locally so parser improvements take effect
        # immediately without bypassing the 30-minute network throttle.
        if cached and isinstance(cached.get("raw"), str):
            decoded_layers = parse_cloud_layers(str(cached["raw"]))
            decoded_text = spoken_text(decoded_layers)
            if cached.get("layers") != decoded_layers or cached.get("text") != decoded_text:
                cached["layers"] = decoded_layers
                cached["text"] = decoded_text
                write_json_atomic(cache_path, cached)
        attempt_age = timestamp_age_seconds(cached, "last_attempt_at") if cached else None
        if attempt_age is None and cached:
            attempt_age = timestamp_age_seconds(cached, "fetched_at")
        if cached and attempt_age is not None and attempt_age < MIN_FETCH_INTERVAL_SECONDS:
            cached["cache_status"] = "fresh"
            return cached

        try:
            current = fetch_clouds(lat, lon)
        except Exception as exc:
            if cached:
                fetched_age = timestamp_age_seconds(cached, "fetched_at")
                cached["cache_status"] = "stale"
                cached["last_attempt_at"] = utc_now().isoformat().replace("+00:00", "Z")
                cached["last_error"] = f"{type(exc).__name__}: {exc}"
                if fetched_age is None or fetched_age > MAX_STALE_AGE_SECONDS:
                    cached["cache_status"] = "stale_expired"
                    cached["text"] = ""
                    cached["layers"] = []
                write_json_atomic(cache_path, cached)
                return cached
            unavailable = {
                "fetched_at": None,
                "last_attempt_at": utc_now().isoformat().replace("+00:00", "Z"),
                "source": "AWC GFA model-derived cloud grid",
                "layers": [],
                "text": "",
                "cache_status": "unavailable",
                "last_error": f"{type(exc).__name__}: {exc}",
            }
            write_json_atomic(cache_path, unavailable)
            return unavailable

        current["cache_status"] = "refreshed"
        write_json_atomic(cache_path, current)
        return current


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yaml"))
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    args = parser.parse_args()

    config: dict[str, object] = {}
    try:
        loaded = yaml.safe_load(args.config.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            config = loaded
    except OSError:
        pass
    station = config.get("station", {})
    station = station if isinstance(station, dict) else {}
    latitude = args.lat if args.lat is not None else float(station.get("latitude", DEFAULT_LAT))
    longitude = args.lon if args.lon is not None else float(station.get("longitude", DEFAULT_LON))
    if latitude == 0.0 and longitude == 0.0:
        parser.error("configure station.latitude and station.longitude before requesting AWC clouds")

    result = refresh(args.cache, args.lock, latitude, longitude)
    print(result.get("text", ""))
    if result.get("last_error"):
        print(result["last_error"], file=os.sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
