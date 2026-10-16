#!/bin/bash
set -u

BASE=${MYAWOS_BASE:-/home/user/weather_station}
CAMERA=${MYAWOS_CAMERA_DIR:-/home/user/weather_camera}
FAA_ACCESS=${MYAWOS_PUBLISH_DIR:-/home/user/faa_weather_access}

# Avoid overlapping runs and mixed-generation output files.
exec 9>"$BASE/.weather_loop.lock"
/usr/bin/flock -n 9 || exit 0

/usr/bin/python3 "$BASE/weather.py" --config "$BASE/config.yaml" --base "$BASE"
/usr/bin/python3 "$BASE/get_clouds_from_awc.py" --config "$BASE/config.yaml" \
  --cache "$BASE/clouds.json" --lock "$BASE/.clouds.lock"
/usr/bin/perl "$BASE/convert_weather_txt_to_wav.pl"
/usr/bin/perl "$BASE/convert_weather_txt_to_sms.pl"
/bin/bash "$BASE/generate.sh"

# Render text and image from the same completed weather/cloud snapshot.
/usr/bin/python3 "$BASE/awos_to_image.py" --input "$BASE/current_sms.txt" --output "$CAMERA/awos.png"

# Publish local artifacts atomically so readers never see partial files.
/usr/bin/ffmpeg -loglevel panic -y -i "$BASE/current.wav" -vn -ac 1 -ar 8000 "$CAMERA/.current.tmp.mp3" && \
  /bin/mv -f "$CAMERA/.current.tmp.mp3" "$CAMERA/current.mp3"
/bin/cp "$BASE/current.wav" "$CAMERA/.current.tmp.wav" && \
  /bin/mv -f "$CAMERA/.current.tmp.wav" "$CAMERA/current.wav"
/bin/cp "$BASE/current_sms.txt" "$FAA_ACCESS/.current_sms.tmp.txt" && \
  /bin/mv -f "$FAA_ACCESS/.current_sms.tmp.txt" "$FAA_ACCESS/current_sms.txt"

# Add an explicitly configured delivery step here only if another host needs a
# copy. No private network address is enabled in the public source.
