# myawos.com
# dennis cox May 2026
# AirSpy R2 SDR click detector using config.yaml

import numpy as np
import subprocess
import time
import logging
import os
import yaml
import serial
import glob
from collections import deque


#########################
# LOAD CONFIG
#########################

CONFIG_PATH = "/home/weather/config.yaml"

def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

config = load_config(CONFIG_PATH)


#########################
# CONFIGURATION
#########################

FREQ_MHZ = config["radio"]["frequency_mhz"]
REQUIRED_CLICKS = int(config["radio"]["required_clicks"])
CLICK_WINDOW = float(config["radio"]["click_window_seconds"])
COOLDOWN = float(config["radio"]["cooldown_seconds"])

SAMPLE_RATE = str(config["sdr"]["sample_rate"])
THRESHOLD_ON = float(config["sdr"]["threshold_on"])
THRESHOLD_OFF = float(config["sdr"]["threshold_off"])
MIN_CLICK_GAP = float(config["sdr"]["min_click_gap_seconds"])
MIN_QUIET_TIME = float(config["sdr"]["min_quiet_time_seconds"])

AUDIO_PATH = config["audio"]["file"]
APLAY_TIMEOUT_SEC = float(config["audio"]["timeout_seconds"])
MAX_TX_TIME = float(config["audio"]["max_tx_seconds"])

PTT_METHOD = config["ptt"]["method"]

ENABLE_PTT_SCRIPT = config["ptt"].get("enable_script")
DISABLE_PTT_SCRIPT = config["ptt"].get("disable_script")

USB_RELAY_PORT = config["ptt"].get("port", "auto")
USB_RELAY_BAUD = int(config["ptt"].get("baud", 9600))
USB_RELAY_ON_HEX = config["ptt"].get("on_command_hex", "A0 01 01 A2")
USB_RELAY_OFF_HEX = config["ptt"].get("off_command_hex", "A0 01 00 A1")

usb_relay_serial = None

LOG_DIR = config["logging"]["directory"]
LOG_PREFIX = config["logging"]["filename_prefix"]


#######################
# LOGGING
#######################

os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(
    LOG_DIR,
    time.strftime("%Y-%m-%d") + f"_{LOG_PREFIX}.log"
)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)

def log(msg):
    logging.info(msg)


######################
# PTT FUNCTIONS
######################
def find_usb_relay_port():
    """
    Finds a likely USB relay serial port.

    Best case:
    - use /dev/serial/by-id/*

    Fallback:
    - use /dev/ttyUSB*
    - use /dev/ttyACM*
    """

    if USB_RELAY_PORT != "auto":
        return USB_RELAY_PORT

    by_id = sorted(glob.glob("/dev/serial/by-id/*"))
    if by_id:
        return by_id[0]

    tty_usb = sorted(glob.glob("/dev/ttyUSB*"))
    if tty_usb:
        return tty_usb[0]

    tty_acm = sorted(glob.glob("/dev/ttyACM*"))
    if tty_acm:
        return tty_acm[0]

    return None


def open_usb_relay():
    global usb_relay_serial

    if usb_relay_serial and usb_relay_serial.is_open:
        return usb_relay_serial

    port = find_usb_relay_port()
    if not port:
        raise RuntimeError("USB relay port not found")

    log(f"Opening USB relay on {port}")

    usb_relay_serial = serial.Serial(
        port,
        USB_RELAY_BAUD,
        timeout=1
    )

    time.sleep(0.2)
    return usb_relay_serial


def usb_relay_send(hex_command):
    ser = open_usb_relay()
    cmd_bytes = bytes.fromhex(hex_command)
    ser.write(cmd_bytes)
    ser.flush()

def ptt_on():
    if PTT_METHOD == "scripts":
        subprocess.run(["python3", ENABLE_PTT_SCRIPT], check=False)
        log("PTT Enabled using scripts")

    elif PTT_METHOD == "usb_relay":
        usb_relay_send(USB_RELAY_ON_HEX)
        log("PTT Enabled using USB relay")

    else:
        raise RuntimeError(f"Unknown PTT method: {PTT_METHOD}")


def ptt_off():
    if PTT_METHOD == "scripts":
        subprocess.run(["python3", DISABLE_PTT_SCRIPT], check=False)
        log("PTT Disabled using scripts")

    elif PTT_METHOD == "usb_relay":
        usb_relay_send(USB_RELAY_OFF_HEX)
        log("PTT Disabled using USB relay")

    else:
        raise RuntimeError(f"Unknown PTT method: {PTT_METHOD}")


######################
# START AIRSPY
######################

cmd = [
    "airspy_rx",
    "-f", FREQ_MHZ,
    "-a", SAMPLE_RATE,
    "-r", "-"
]

log(f"Starting Airspy: {' '.join(cmd)}")

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE
)


########################
# STATE VARIABLES
########################

click_times = deque()
carrier_active = False
carrier_went_quiet_at = time.time()
last_click_time = 0
last_trigger_time = 0

log(f"Listening for {REQUIRED_CLICKS} clicks within {CLICK_WINDOW} seconds...")


#########################
# MAIN LOOP
#########################

while True:
    data = proc.stdout.read(8192)
    if not data:
        continue

    samples = np.frombuffer(data, dtype=np.int16)

    amp = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
    now = time.time()

    if carrier_active:
        if amp < THRESHOLD_OFF:
            carrier_active = False
            carrier_went_quiet_at = now
        continue

    quiet_long_enough = (now - carrier_went_quiet_at) >= MIN_QUIET_TIME
    click_gap_ok = (now - last_click_time) >= MIN_CLICK_GAP

    if amp > THRESHOLD_ON and quiet_long_enough and click_gap_ok:
        carrier_active = True
        last_click_time = now

        click_times.append(now)

        # remove old clicks
        while click_times and now - click_times[0] > CLICK_WINDOW:
            click_times.popleft()

        log(f"Click {len(click_times)} amp={amp:.0f}")

        if len(click_times) >= REQUIRED_CLICKS:
            if now - last_trigger_time >= COOLDOWN:
                log("TRIGGER: play weather")
                last_trigger_time = now
                click_times.clear()

                start_tx = time.time()

                try:
                    ptt_on()

                    subprocess.run(
                        ["aplay", AUDIO_PATH],
                        check=False,
                        timeout=APLAY_TIMEOUT_SEC
                    )

                except subprocess.TimeoutExpired:
                    log("Audio timeout - forcing PTT off")

                finally:
                    if time.time() - start_tx > MAX_TX_TIME:
                        log("Max TX exceeded - forcing shutdown")

                    try:
                        ptt_off()
                    except Exception as e:
                        log(f"ERROR: failed to disable PTT: {e}")


            else:
                log("Ignored: cooldown active")
                click_times.clear()

                
