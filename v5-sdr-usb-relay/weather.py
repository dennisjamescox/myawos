import json
import urllib.request
from datetime import datetime, timezone
import weatherlink_live_local as wlll

# Updated dcox 6/06/2026
# Changes:
#  new error file to store so it doesn't overwrite weather
#  altimeter now provides two digit on float



WEATHER_TXT_PATH = "/home/user/weather_station/weather.txt"
ERROR_PATH = "/home/user/weather_station/weather_error.txt"
STATE_PATH = "/home/user/weather_station/weatherlink_state.json"  # stores ip + last_wind_dir
PORT = 80
JSON_TIMEOUT_SEC = 2.0

MPH_TO_KT = 0.868976
CALM_KT_THRESHOLD = 1.0  # below this, hold last direction
DIR_ROUND_DEG = 10       # round down to nearest 10 degrees


def write_error(msg: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    with open(ERROR_PATH,"w") as f:
        print(f"{timestamp} {msg}", file=f)
        
def load_state(path: str) -> dict:
    try:
        with open(path, "r") as f:
            st = json.load(f)
            return st if isinstance(st, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def save_state(path: str, state: dict) -> None:
    try:
        with open(path, "w") as f:
            json.dump(state, f)
    except Exception:
        pass  # don't fail run if state can't be written

def discover_ip_via_wlll():
    try:
        devices = wlll.discover()
        if not devices:
            return None
        return devices[0].ip_addresses[0]
    except Exception:
        return None

def http_get_current_conditions(ip: str) -> dict:
    url = f"http://{ip}:{PORT}/v1/current_conditions"
    req = urllib.request.Request(
        url=url,
        method="GET",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=JSON_TIMEOUT_SEC) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)

def find_record(conditions: list, data_structure_type: int, txid: int | None = None) -> dict | None:
    for rec in conditions:
        if not isinstance(rec, dict):
            continue
        if rec.get("data_structure_type") != data_structure_type:
            continue
        if txid is not None and rec.get("txid") != txid:
            continue
        return rec
    return None

def f_to_c(f: float) -> float:
    return (f - 32.0) * (5.0 / 9.0)

def normalize_dir_deg(deg: float) -> int:
    """
    Normalize to 0..359, then round DOWN to nearest DIR_ROUND_DEG.
    Ensures 360 never appears (becomes 000).
    """
    # normalize
    d = int(deg) % 360
    # round down
    d = (d // DIR_ROUND_DEG) * DIR_ROUND_DEG
    # re-normalize just in case
    d = d % 360
    return d

def main() -> None:
    state = load_state(STATE_PATH)
    ip = state.get("ip")

    # If no cached IP, discover now
    if not ip:
        ip = discover_ip_via_wlll()
        if not ip:
            write_error("Error getting weather from station")
            return
        state["ip"] = ip
        save_state(STATE_PATH, state)

    # JSON-first attempt
    payload = None
    try:
        payload = http_get_current_conditions(ip)
    except Exception:
        payload = None

    # If JSON failed, discover IP via original API, update state, retry once
    if payload is None:
        new_ip = discover_ip_via_wlll()
        if new_ip:
            ip = new_ip
            state["ip"] = ip
            save_state(STATE_PATH, state)
            try:
                payload = http_get_current_conditions(ip)
            except Exception:
                payload = None

    if payload is None:
        write_error("Error getting weather from station")
        return

    data = payload.get("data") or {}
    conditions = data.get("conditions") or []
    if not isinstance(conditions, list) or not conditions:
        write_error("Error getting weather from station")
        return

    # Your JSON:
    # - data_structure_type 1 with txid:1 for outdoor suite
    # - data_structure_type 3 for barometer
    iss = find_record(conditions, 1, txid=1) or find_record(conditions, 1)
    bar = find_record(conditions, 3)

    if not iss or not bar:
        write_error("Error getting weather from station")
        return

    # ---- Time ----
    zulutime = datetime.now(timezone.utc)
    hours_minutes = zulutime.strftime("%H%M")

    # ---- Wind (1-minute avg) ----
    try:
        wind_dir_1min = float(iss.get("wind_dir_scalar_avg_last_1_min"))
        wind_mph_1min = float(iss.get("wind_speed_avg_last_1_min"))
        gust_mph_2 = float(iss.get("wind_speed_hi_last_2_min"))
    except Exception:
        write_error("Error getting weather from station")
        return

    wind_kt_1min = wind_mph_1min * MPH_TO_KT
    gust_kt_2 = gust_mph_2 * MPH_TO_KT

    # Direction handling:
    # - If calm (< 1 kt), keep last non-calm direction (from state) if available
    # - Else compute rounded direction and store it
    last_dir = state.get("last_wind_dir")  # expected int 0..359
    if wind_kt_1min < CALM_KT_THRESHOLD and isinstance(last_dir, int):
        dir_out = last_dir
    else:
        dir_out = normalize_dir_deg(wind_dir_1min)
        state["last_wind_dir"] = dir_out
        save_state(STATE_PATH, state)

    # ---- Pressure / altimeter (inHg, already sea-level) ----
    try:
        altimeter = round(float(bar.get("bar_sea_level")), 2)
    except Exception:
        write_error("Error getting weather from station")
        return

    # ---- Temp / Dewpoint ----
    # JSON is °F -> convert to °C to match your original output style
    try:
        temp_c = round(f_to_c(float(iss.get("temp"))))
        dew_c = round(f_to_c(float(iss.get("dew_point"))))
    except Exception:
        write_error("Error getting weather from station")
        return

    # ---- Write output file (same line order as your old script) ----
    with open(WEATHER_TXT_PATH, "w") as weatherFile:
        print(f"{hours_minutes}", file=weatherFile)
        print(f"{dir_out:03}", file=weatherFile)
        print(f"{round(wind_kt_1min)}", file=weatherFile)
        print(f"{round(gust_kt_2)}", file=weatherFile)
        print(f"{altimeter:.2f}", file=weatherFile)
        print(f"{temp_c}", file=weatherFile)
        print(f"{dew_c}", file=weatherFile)

if __name__ == "__main__":
    main()
