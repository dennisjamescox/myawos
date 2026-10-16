import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "get_clouds_from_awc.py"
SPEC = importlib.util.spec_from_file_location("get_clouds_from_awc", MODULE_PATH)
clouds = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(clouds)


class CloudParsingTests(unittest.TestCase):
    def test_parses_current_gfa_example(self):
        layers = clouds.parse_cloud_layers("BKN040/TOP FL450/CI ABV")
        self.assertEqual(layers[0]["code"], "BKN")
        self.assertEqual(layers[0]["base_msl_ft"], 4000)
        self.assertEqual(layers[1]["top_msl_ft"], 45000)
        self.assertTrue(layers[2]["above_fl180"])
        self.assertEqual(
            clouds.spoken_text(layers),
            "AWC Estimated clouds: Broken at 4,000 feet MSL. "
            "Tops at 45,000 feet MSL. Cirrus clouds above flight level one eight zero.",
        )

    def test_parses_spelled_out_cirrus_from_live_payload(self):
        layers = clouds.parse_cloud_layers("Cirrus")
        self.assertEqual(layers, [{"kind": "cirrus", "above_fl180": False}])
        self.assertEqual(clouds.spoken_text(layers), "AWC Estimated clouds: Cirrus clouds.")

    def test_redecodes_cached_raw_without_fetching(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "clouds.json"
            lock = root / ".clouds.lock"
            result = {
                "fetched_at": clouds.utc_now().isoformat(),
                "last_attempt_at": clouds.utc_now().isoformat(),
                "raw": "Cirrus",
                "layers": [{"kind": "unknown", "raw": "Cirrus"}],
                "text": "",
            }
            cache.write_text(json.dumps(result), encoding="utf-8")
            with patch.object(clouds, "fetch_clouds") as fetch:
                output = clouds.refresh(cache, lock, 29.751, -94.877)
            fetch.assert_not_called()
            self.assertEqual(output["text"], "AWC Estimated clouds: Cirrus clouds.")

    def test_cache_blocks_a_second_fetch_inside_thirty_minutes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "clouds.json"
            lock = root / ".clouds.lock"
            result = {
                "fetched_at": clouds.utc_now().isoformat(),
                "last_attempt_at": clouds.utc_now().isoformat(),
                "layers": [{"kind": "layer", "code": "CLR", "description": "Clear"}],
                "text": "AWC Estimated clouds: Clear.",
            }
            cache.write_text(json.dumps(result), encoding="utf-8")
            with patch.object(clouds, "fetch_clouds") as fetch:
                output = clouds.refresh(cache, lock, 29.751, -94.877)
            fetch.assert_not_called()
            self.assertEqual(output["cache_status"], "fresh")

    def test_failed_first_attempt_is_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "clouds.json"
            lock = root / ".clouds.lock"
            with patch.object(clouds, "fetch_clouds", side_effect=RuntimeError("offline")):
                output = clouds.refresh(cache, lock, 29.751, -94.877)
            self.assertEqual(output["cache_status"], "unavailable")
            self.assertTrue(cache.exists())

            with patch.object(clouds, "fetch_clouds") as fetch:
                clouds.refresh(cache, lock, 29.751, -94.877)
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
