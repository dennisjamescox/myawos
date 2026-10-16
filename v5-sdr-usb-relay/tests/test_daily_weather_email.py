import importlib.util
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


MODULE_PATH = Path(__file__).parents[1] / "daily_weather_email.py"
SPEC = importlib.util.spec_from_file_location("daily_weather_email", MODULE_PATH)
daily = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(daily)


class DailyWeatherEmailTests(unittest.TestCase):
    def test_sunrise_schedule_uses_configured_offset(self):
        config = {
            "timezone": "America/Chicago",
            "location": {"latitude": 29.7618, "longitude": -94.8484},
            "schedule": {"sunrise_offset_minutes": 10},
        }
        sunrise = daily.sunrise_time(date(2026, 6, 21), 29.7618, -94.8484, ZoneInfo("America/Chicago"))
        scheduled = daily.scheduled_send_time(config, date(2026, 6, 21))
        self.assertEqual((scheduled - sunrise).total_seconds(), 600)

    def test_parses_nbm_hourly_values(self):
        block = [
            " KEFD   NBM V5.0 NBH GUIDANCE    9/13/2026  1100 UTC",
            " UTC  12 13 14",
            " TMP  79 81 84",
            " DPT  77 79 79",
            " WDR  14 14 16",
            " WSP   0  1  3",
            " GST   3  4  4",
            " SKY  18 11 16",
            " P01   1  1  1",
            " T01   2  3  3",
            " LCB  60 60120",
            " VIS 100 90100",
        ]
        issued, rows = daily.parse_nbm(block, ZoneInfo("America/Chicago"))
        self.assertEqual(issued, "2026-09-13 11:00 UTC")
        self.assertEqual([row["TMP"] for row in rows], [79, 81, 84])
        self.assertEqual([row["LCB"] for row in rows], [60, 60, 120])
        self.assertEqual([row["VIS"] for row in rows], [100, 90, 100])

    def test_counts_request_events_once(self):
        zone = ZoneInfo("America/Chicago")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "2026-09-13_sdr_click.log"
            path.write_text(
                "2026-09-13 06:59:59,000 Weather request accepted\n"
                "2026-09-13 07:15:00,000 Weather request accepted\n"
                "2026-09-13 07:15:01,000 One-shot TX handed off; detector exiting\n"
                "2026-09-13 08:00:00,000 Click 1 level=-40 dBFS\n"
            )
            found = daily.radio_requests(
                Path(directory),
                datetime(2026, 9, 13, 7, 0, tzinfo=zone),
                datetime(2026, 9, 14, 7, 0, tzinfo=zone),
            )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].hour, 7)


if __name__ == "__main__":
    unittest.main()
