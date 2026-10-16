import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "hackrf_transmit_requested.py"
SPEC = importlib.util.spec_from_file_location("hackrf_transmit_requested", MODULE_PATH)
requested = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(requested)


class RequestedTransmissionTests(unittest.TestCase):
    def make_config(self, marker: Path, enabled=True):
        return {
            "radio": {"frequency_mhz": "122.700000"},
            "sdr": {"serial": "test-serial"},
            "audio": {"file": "/tmp/current.wav", "timeout_seconds": 45, "max_tx_seconds": 50},
            "transmission": {
                "method": "systemd_handoff",
                "script": "/tmp/hackrf_transmit_once.py",
                "request_file": str(marker),
            },
            "safety": {"transmit_enabled": enabled, "contained_rf_confirmed": True},
        }

    @patch.object(requested.subprocess, "run")
    def test_consumes_request_before_one_transmission(self, run_mock):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "tx.request"
            marker.write_text("requested\n")
            self.assertTrue(requested.consume_and_transmit(self.make_config(marker)))
            self.assertFalse(marker.exists())
            run_mock.assert_called_once()

    @patch.object(requested.subprocess, "run")
    def test_no_request_means_no_transmission(self, run_mock):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "tx.request"
            self.assertFalse(requested.consume_and_transmit(self.make_config(marker)))
            run_mock.assert_not_called()

    @patch.object(requested.subprocess, "run")
    def test_disabled_gate_discards_request(self, run_mock):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "tx.request"
            marker.write_text("requested\n")
            self.assertFalse(requested.consume_and_transmit(self.make_config(marker, enabled=False)))
            self.assertFalse(marker.exists())
            run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
