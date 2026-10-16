#!/usr/bin/env python3
"""Build and send the daily MyAWOS weather and radio-usage email."""

from __future__ import annotations

import argparse
import email.policy
import fcntl
import html
import json
import math
import re
import shutil
import smtplib
import ssl
import sys
import time
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
import yaml


REQUEST_EVENTS = (
    "Weather request accepted",
    "One-shot TX handed off; detector exiting",
    "Stopping HackRF receive stream for one contained transmission",
)
NBM_ROOT = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/blend/prod"


def sunrise_time(day: date, latitude: float, longitude: float, zone: ZoneInfo) -> datetime:
    """Return local civil sunrise using the NOAA sunrise equation."""
    day_number = day.timetuple().tm_yday
    longitude_hour = longitude / 15.0
    approximate = day_number + ((6.0 - longitude_hour) / 24.0)
    mean_anomaly = (0.9856 * approximate) - 3.289
    true_longitude = (
        mean_anomaly
        + 1.916 * math.sin(math.radians(mean_anomaly))
        + 0.020 * math.sin(math.radians(2 * mean_anomaly))
        + 282.634
    ) % 360
    right_ascension = math.degrees(
        math.atan(0.91764 * math.tan(math.radians(true_longitude)))
    ) % 360
    longitude_quadrant = math.floor(true_longitude / 90) * 90
    ascension_quadrant = math.floor(right_ascension / 90) * 90
    right_ascension = (right_ascension + longitude_quadrant - ascension_quadrant) / 15
    sin_declination = 0.39782 * math.sin(math.radians(true_longitude))
    cos_declination = math.cos(math.asin(sin_declination))
    cos_hour_angle = (
        math.cos(math.radians(90.833))
        - sin_declination * math.sin(math.radians(latitude))
    ) / (cos_declination * math.cos(math.radians(latitude)))
    if not -1 <= cos_hour_angle <= 1:
        raise ValueError("Sunrise is not defined for this date and location")
    hour_angle = (360 - math.degrees(math.acos(cos_hour_angle))) / 15
    local_mean_time = hour_angle + right_ascension - (0.06571 * approximate) - 6.622
    utc_hours = (local_mean_time - longitude_hour) % 24
    utc_midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return (utc_midnight + timedelta(hours=utc_hours)).astimezone(zone)


def scheduled_send_time(config: dict[str, Any], day: date) -> datetime:
    zone = ZoneInfo(str(config.get("timezone", "America/Chicago")))
    location = config["location"]
    offset = float(config.get("schedule", {}).get("sunrise_offset_minutes", 10))
    return sunrise_time(day, float(location["latitude"]), float(location["longitude"]), zone) + timedelta(minutes=offset)


def file_health(name: str, path: Path, now: datetime, max_age_minutes: float) -> dict[str, Any]:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime, now.tzinfo)
        age_minutes = max(0.0, (now - modified).total_seconds() / 60)
        good = path.is_file() and path.stat().st_size > 0 and age_minutes <= max_age_minutes
        detail = f"Updated {modified.strftime('%-I:%M %p %Z')} ({age_minutes:.0f} min ago)"
        if not good:
            detail = f"STALE — {detail}"
    except OSError as exc:
        good = False
        detail = f"Unavailable — {exc}"
    return {"name": name, "good": good, "detail": detail}


def disk_health_warning(path: Path, warning_percent: float) -> dict[str, Any] | None:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    used_percent = (usage.used / usage.total * 100) if usage.total else 0
    if used_percent < warning_percent:
        return None
    return {
        "name": "Disk storage",
        "good": False,
        "detail": (
            f"{used_percent:.1f}% used — {usage.free / (1024 ** 3):.1f} GB free; "
            f"warning threshold {warning_percent:g}%"
        ),
    }


def system_health(config: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    status_config = config.get("status", {})
    max_age = float(status_config.get("max_file_age_minutes", 30))
    weather_source = Path(config.get("weather_source", config["weather_report"]))
    weather_max_age_minutes = float(config.get("weather_max_age_hours", 12)) * 60
    results = [
        file_health("Weather station", weather_source, now, weather_max_age_minutes),
        file_health("FAA camera", Path(config["camera_image"]), now, max_age),
    ]
    piaware_url = str(status_config.get("piaware_status_url", "http://piaware.local/status.json"))
    try:
        response = requests.get(piaware_url, timeout=float(status_config.get("piaware_timeout_seconds", 5)))
        response.raise_for_status()
        payload = response.json()
        piaware = payload.get("piaware", {})
        radio = payload.get("radio", {})
        good = piaware.get("status") == "green" and radio.get("status") == "green"
        detail = f"{piaware.get('message', 'PiAware status unknown')}; {radio.get('message', 'radio status unknown')}"
    except Exception as exc:
        good = False
        detail = f"Unavailable — {exc}"
    results.append({"name": "PiAware", "good": good, "detail": detail})
    disk_path = Path(status_config.get("disk_path", Path(config["camera_image"]).parent))
    warning_percent = float(status_config.get("disk_warning_percent", 75))
    disk_warning = disk_health_warning(disk_path, warning_percent)
    if disk_warning:
        results.append(disk_warning)
    return results


def health_html(results: list[dict[str, Any]]) -> str:
    all_good = all(item["good"] for item in results)
    disk_warning = next((item for item in results if item["name"] == "Disk storage"), None)
    overall = (
        "🟢 🟢 🟢 All three systems are good"
        if all_good
        else f"⚠️ Disk storage warning — {disk_warning['detail']}"
        if disk_warning
        else "⚠️ One or more systems need attention"
    )
    overall_class = "all-good" if all_good else "attention"
    cards = "".join(
        f'<div class="health-card {"good" if item["good"] else "bad"}">'
        f'<strong>{"🟢" if item["good"] else "🔴"} {html.escape(item["name"])}</strong>'
        f'<span>{html.escape(item["detail"])}</span></div>'
        for item in results
    )
    return f'<div class="health-overall {overall_class}">{overall}</div><div class="health-grid">{cards}</div>'


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid configuration: {path}")
    return config


def read_text(path: Path, fallback: str) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return f"{fallback}: {exc}"
    return value or fallback


def radio_requests(log_directory: Path, start: datetime, end: datetime) -> list[datetime]:
    found: list[datetime] = []
    for path in sorted(log_directory.glob("*_sdr_click.log")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not any(event in line for event in REQUEST_EVENTS):
                continue
            try:
                naive = datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")
            except ValueError:
                continue
            stamp = naive.replace(tzinfo=start.tzinfo)
            if start <= stamp < end:
                found.append(stamp)
    unique: list[datetime] = []
    for stamp in sorted(set(found)):
        # Older deployments logged both the trigger and the TX handoff. Treat
        # events from the same activation window as one weather request.
        if not unique or (stamp - unique[-1]).total_seconds() > 5:
            unique.append(stamp)
    return unique


def available_cycles(session: requests.Session, day: datetime) -> list[int]:
    url = f"{NBM_ROOT}/blend.{day:%Y%m%d}/"
    response = session.get(url, timeout=20)
    response.raise_for_status()
    return sorted({int(value) for value in re.findall(r'href="(\d{2})/"', response.text)}, reverse=True)


def extract_station_block(response: requests.Response, station: str) -> list[str]:
    header = re.compile(rf"^\s{re.escape(station)}\s+NBM\s+V\S+\s+NBH\s+GUIDANCE")
    next_header = re.compile(r"^\s[A-Z0-9]{4}\s+NBM\s+V\S+\s+NBH\s+GUIDANCE")
    lines: list[str] = []
    for raw in response.iter_lines(decode_unicode=True):
        line = raw if isinstance(raw, str) else raw.decode("ascii", errors="replace")
        if not lines:
            if header.match(line):
                lines.append(line.rstrip())
            continue
        if next_header.match(line) or (not line.strip() and len(lines) > 2):
            break
        lines.append(line.rstrip())
    return lines


def fetch_nbm_hourly(station: str, now_utc: datetime) -> tuple[list[str], str]:
    station = station.upper()
    session = requests.Session()
    session.headers["User-Agent"] = "MyAWOS-Daily-Weather/1.0"
    for days_back in (0, 1):
        day = now_utc - timedelta(days=days_back)
        try:
            cycles = available_cycles(session, day)
        except requests.RequestException:
            continue
        for cycle in cycles:
            issued = datetime(day.year, day.month, day.day, cycle, tzinfo=timezone.utc)
            if issued > now_utc:
                continue
            url = f"{NBM_ROOT}/blend.{day:%Y%m%d}/{cycle:02d}/text/blend_nbhtx.t{cycle:02d}z"
            try:
                with session.get(url, stream=True, timeout=(15, 90)) as response:
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    block = extract_station_block(response, station)
            except requests.RequestException:
                continue
            if block:
                return block, url
    raise RuntimeError(f"No current NOAA NBM hourly bulletin found for {station}")


def fixed_width_values(line: str) -> list[int | None]:
    values: list[int | None] = []
    # NBM rows begin with one space, a three-character label, then a space.
    payload = line[5:]
    for offset in range(0, len(payload), 3):
        value = payload[offset : offset + 3].strip()
        try:
            values.append(int(value))
        except ValueError:
            values.append(None)
    return values


def parse_nbm(block: list[str], local_zone: ZoneInfo) -> tuple[str, list[dict[str, Any]]]:
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{4}) UTC", block[0])
    if not match:
        raise ValueError("NBM issue time was not recognized")
    issued = datetime.strptime(" ".join(match.groups()), "%m/%d/%Y %H%M").replace(tzinfo=timezone.utc)
    rows: dict[str, list[int | None]] = {}
    for line in block[1:]:
        label = line[:4].strip()
        if label:
            rows[label] = fixed_width_values(line)
    count = len(rows.get("UTC", []))
    forecast: list[dict[str, Any]] = []
    for index in range(count):
        item: dict[str, Any] = {"time": (issued + timedelta(hours=index + 1)).astimezone(local_zone)}
        for key in ("TMP", "DPT", "WDR", "WSP", "GST", "SKY", "P01", "T01", "LCB", "VIS"):
            values = rows.get(key, [])
            item[key] = values[index] if index < len(values) else None
        forecast.append(item)
    return issued.strftime("%Y-%m-%d %H:%M UTC"), forecast


def value_or_dash(value: Any, suffix: str = "") -> str:
    return "—" if value is None or value in (-88, -99) else f"{value}{suffix}"


def wind_text(item: dict[str, Any]) -> str:
    speed = item.get("WSP")
    direction = item.get("WDR")
    if speed == 0:
        return "Calm"
    if speed is None or direction is None:
        return "—"
    gust = item.get("GST")
    text = f"{direction * 10:03d}° at {speed} kt"
    if gust is not None and gust > speed:
        text += f", gust {gust}"
    return text


def forecast_rows(forecast: list[dict[str, Any]], start: datetime, end: datetime) -> str:
    selected = [item for item in forecast if start <= item["time"] <= end]
    if not selected:
        return '<tr><td colspan="9">No forecast hours fall in the reporting period.</td></tr>'
    result: list[str] = []
    for item in selected:
        cloud_base = item.get("LCB")
        visibility = item.get("VIS")
        result.append(
            "<tr>"
            f"<td>{html.escape(item['time'].strftime('%a %I %p'))}</td>"
            f"<td>{value_or_dash(item.get('TMP'), '°F')}</td>"
            f"<td>{value_or_dash(item.get('DPT'), '°F')}</td>"
            f"<td>{html.escape(wind_text(item))}</td>"
            f"<td>{value_or_dash(item.get('SKY'), '%')}</td>"
            f"<td>{value_or_dash(item.get('P01'), '%')}</td>"
            f"<td>{value_or_dash(item.get('T01'), '%')}</td>"
            f"<td>{'—' if cloud_base in (None, -88, -99) else f'{cloud_base * 100:,} ft'}</td>"
            f"<td>{'—' if visibility in (None, -88, -99) else f'{visibility / 10:g} mi'}</td>"
            "</tr>"
        )
    return "".join(result)


def build_report(config: dict[str, Any], now: datetime) -> tuple[EmailMessage, str]:
    zone = ZoneInfo(str(config.get("timezone", "America/Chicago")))
    local_now = now.astimezone(zone)
    period_end = local_now
    period_start = period_end - timedelta(hours=24)
    airport = str(config.get("airport", "54T")).upper()
    forecast_config = config["forecast"]
    forecast_station = str(forecast_config.get("station", "KEFD")).upper()
    forecast_label = str(forecast_config.get("label", forecast_station))
    weather = read_text(Path(config["weather_report"]), "Weather report unavailable")
    requests_found = radio_requests(Path(config["request_log_directory"]), period_start, period_end)
    health = system_health(config, local_now)

    forecast_error = ""
    issued = "unavailable"
    forecast: list[dict[str, Any]] = []
    source_url = ""
    try:
        block, source_url = fetch_nbm_hourly(forecast_station, now.astimezone(timezone.utc))
        issued, forecast = parse_nbm(block, zone)
    except Exception as exc:
        forecast_error = str(exc)

    subject = f"Daily {local_now:%Y-%m-%d} {airport} Weather Report"
    footer = f"Automated at {local_now.strftime('%Y-%m-%d %I:%M:%S %p %Z')}."
    request_list = "".join(
        f"<li>{html.escape(stamp.strftime('%Y-%m-%d %I:%M:%S %p %Z'))}</li>" for stamp in requests_found
    ) or "<li>No radio weather requests during this period.</li>"
    forecast_start = local_now.replace(minute=0, second=0, microsecond=0)
    forecast_end = forecast_start + timedelta(hours=24)
    forecast_body = (
        f'<p class="error">Forecast unavailable: {html.escape(forecast_error)}</p>'
        if forecast_error
        else f"""
        <p>NOAA NBM hourly model guidance for {html.escape(forecast_label)}. Model issued {html.escape(issued)}.</p>
        <table><thead><tr><th>Time</th><th>Temp</th><th>Dewpoint</th><th>Wind</th><th>Sky</th><th>Rain</th><th>T-storm</th><th>Cloud base</th><th>Visibility</th></tr></thead>
        <tbody>{forecast_rows(forecast, forecast_start, forecast_end)}</tbody></table>
        <p class="source">Source: <a href="{html.escape(source_url)}">NOAA/NCEP operational NBM bulletin</a>. Model guidance is not an observed condition or a substitute for an official aviation briefing.</p>
        """
    )

    body_html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    body{{font-family:Arial,sans-serif;color:#17202a;max-width:1000px;margin:auto}} h1,h2{{color:#17365d}}
    .weather{{white-space:pre-wrap;background:#f3f6f9;border-left:4px solid #3776a8;padding:12px}}
    table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border:1px solid #ccd6df;padding:6px;text-align:left}} th{{background:#e8f0f7}}
    img{{max-width:100%;height:auto}} .source,.footer{{color:#59636e;font-size:12px}} .error{{color:#9c2f20}}
    .health-overall{{margin:16px 0 10px;padding:13px;border-radius:8px;font-size:17px;font-weight:bold;text-align:center}}
    .health-overall.all-good{{color:#17653b;background:#e7f7ed}} .health-overall.attention{{color:#8a2c20;background:#fdebe8}}
    .health-grid{{display:table;width:100%;border-spacing:8px}} .health-card{{display:table-cell;padding:10px;border:1px solid #ccd6df;border-radius:7px}}
    .health-card.good{{border-top:4px solid #2c9b69}} .health-card.bad{{border-top:4px solid #c95252}} .health-card span{{display:block;margin-top:5px;color:#59636e;font-size:12px}}
    </style></head><body>
    <h1>{html.escape(subject)}</h1>
    {health_html(health)}
    <h2>Weather camera</h2><p><img src="cid:weather-camera" alt="Current 54T weather camera image"></p>
    <h2>Current weather report</h2><div class="weather">{html.escape(weather)}</div>
    <h2>Radio weather requests: {len(requests_found)}</h2>
    <p>Reporting period: {html.escape(period_start.strftime('%Y-%m-%d %I:%M %p %Z'))} through {html.escape(period_end.strftime('%Y-%m-%d %I:%M %p %Z'))}</p><ul>{request_list}</ul>
    <h2>{html.escape(airport)} day and night model guidance</h2>{forecast_body}
    <p class="footer">{html.escape(footer)}</p></body></html>"""

    plain_requests = "\n".join(f"- {stamp:%Y-%m-%d %I:%M:%S %p %Z}" for stamp in requests_found) or "- None"
    plain_health = "\n".join(
        f"{'GREEN' if item['good'] else 'RED'} — {item['name']}: {item['detail']}" for item in health
    )
    plain = (
        f"{subject}\n\nSystem status:\n{plain_health}\n\nCurrent weather report:\n{weather}\n\n"
        f"Radio weather requests ({len(requests_found)}):\n{plain_requests}\n\n"
        f"NOAA NBM guidance: {forecast_label}; model issued {issued}.\n"
        f"{('Forecast unavailable: ' + forecast_error) if forecast_error else 'See the HTML portion for the hourly day/night table.'}\n\n{footer}\n"
    )

    message = EmailMessage(policy=email.policy.default)
    message["Subject"] = subject
    message["From"] = config["email"]["from"]
    message["To"] = config["email"]["to"]
    message.set_content(plain)
    message.add_alternative(body_html, subtype="html")
    image_path = Path(config["camera_image"])
    if image_path.exists():
        subtype = "png" if image_path.suffix.lower() == ".png" else "jpeg"
        message.get_payload()[-1].add_related(
            image_path.read_bytes(), maintype="image", subtype=subtype,
            cid="<weather-camera>", filename=image_path.name,
        )
    return message, body_html


def send_message(config: dict[str, Any], message: EmailMessage) -> None:
    smtp = config["smtp"]
    password_path = Path(smtp["password_file"])
    password = "".join(password_path.read_text(encoding="utf-8").split())
    if not password:
        raise RuntimeError(f"SMTP password file is empty: {password_path}")
    context = ssl.create_default_context()
    host, port = str(smtp["host"]), int(smtp["port"])
    if host == "smtp.gmail.com" and len(password) != 16:
        raise RuntimeError("smtp.gmail.com requires a 16-character Google app password")
    if bool(smtp.get("ssl", False)):
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=30, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
    with server:
        server.ehlo()
        if bool(smtp.get("starttls", True)):
            server.starttls(context=context)
            server.ehlo()
        server.login(str(smtp["username"]), password)
        server.send_message(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-eml", type=Path, help="Build a preview message without sending")
    parser.add_argument("--output-html", type=Path, help="Write the rendered HTML alongside a preview")
    parser.add_argument("--scheduled", action="store_true", help="Wait for today's sunrise offset and send once")
    args = parser.parse_args()
    config = load_config(args.config)
    lock_path = Path(config.get("lock_file", "/tmp/myawos-daily-email.lock"))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Daily email is already running", file=sys.stderr)
            return 0
        if args.scheduled:
            zone = ZoneInfo(str(config.get("timezone", "America/Chicago")))
            now_local = datetime.now(timezone.utc).astimezone(zone)
            state_path = Path(config.get("schedule", {}).get(
                "state_file", "/home/user/weather_station/daily_email_last_sent.txt"
            ))
            try:
                if state_path.read_text(encoding="utf-8").strip() == now_local.date().isoformat():
                    print(f"Daily email already sent for {now_local.date().isoformat()}")
                    return 0
            except OSError:
                pass
            target = scheduled_send_time(config, now_local.date())
            wait_seconds = (target - now_local).total_seconds()
            if wait_seconds > 0:
                print(f"Waiting until {target.strftime('%Y-%m-%d %I:%M:%S %p %Z')} (sunrise + offset)", flush=True)
                time.sleep(wait_seconds)
        message, body_html = build_report(config, datetime.now(timezone.utc))
        if args.output_eml:
            args.output_eml.write_bytes(message.as_bytes())
            if args.output_html:
                args.output_html.write_text(body_html, encoding="utf-8")
            print(f"Preview written to {args.output_eml}")
            return 0
        send_message(config, message)
        if args.scheduled:
            zone = ZoneInfo(str(config.get("timezone", "America/Chicago")))
            sent_day = datetime.now(timezone.utc).astimezone(zone).date().isoformat()
            state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = state_path.with_suffix(".tmp")
            temporary.write_text(sent_day + "\n", encoding="utf-8")
            temporary.replace(state_path)
        print(f"Sent {message['Subject']} to {message['To']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
