import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "weather.py"
SPEC = importlib.util.spec_from_file_location("weather", MODULE_PATH)
weather = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(weather)


def payload(timestamp: float | None = 1760616000) -> dict:
    data = {
        "conditions": [
            {
                "data_structure_type": 1,
                "txid": 1,
                "wind_dir_scalar_avg_last_1_min": 174,
                "wind_speed_avg_last_1_min": 10,
                "wind_speed_hi_last_2_min": 15,
                "temp": 77,
                "dew_point": 59,
            },
            {"data_structure_type": 3, "bar_sea_level": 29.92},
        ]
    }
    if timestamp is not None:
        data["ts"] = timestamp
    return {"data": data}


class WeatherTests(unittest.TestCase):
    def test_station_timestamp_is_authoritative(self):
        state = {}
        observed = datetime.fromtimestamp(1760616000, timezone.utc)
        values, observed_at = weather.observation_values(
            payload(), state, now=datetime(2026, 10, 17, tzinfo=timezone.utc)
        )
        self.assertEqual(observed_at, observed)
        self.assertEqual(values, [observed.strftime("%H%M"), "170", "9", "13", "29.92", "25", "15"])

    def test_missing_station_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timestamp"):
            weather.observation_values(payload(None), {})

    @patch.object(weather, "http_get_current_conditions", side_effect=ConnectionError("offline"))
    def test_failed_refresh_preserves_last_good_weather(self, _get):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root / "weather.txt"
            old.write_text("old weather\n", encoding="utf-8")
            config = {"weather": {"host": "192.0.2.10", "port": 80}}

            self.assertEqual(weather.refresh(config, root), 1)
            self.assertEqual(old.read_text(encoding="utf-8"), "old weather\n")
            self.assertIn("offline", (root / "weather_error.txt").read_text(encoding="utf-8"))

    def test_write_weather_uses_observation_time_as_file_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "weather.txt"
            observed = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
            weather.write_weather(path, ["1200", "170", "9", "13", "29.92", "25", "15"], observed)
            self.assertEqual(path.stat().st_mtime, observed.timestamp())


if __name__ == "__main__":
    unittest.main()
