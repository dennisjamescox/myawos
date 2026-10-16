import importlib.util
import logging
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "click_listen.py"
SPEC = importlib.util.spec_from_file_location("click_listen", MODULE_PATH)
click = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(click)


class HackRFLevelTests(unittest.TestCase):
    def make_source(self):
        return click.HackRFSource(
            ["hackrf_transfer"],
            sample_rate=8_000_000,
            tune_offset_hz=100_000,
            channel_rate_hz=20_000,
        )

    def test_target_offset_tone_is_detected_above_noise(self):
        source = self.make_source()
        count = source.chunk_bytes // 2
        n = np.arange(count)
        tone = 35 * np.exp(-1j * 2 * np.pi * 100_000 * n / 8_000_000)
        rng = np.random.default_rng(7)
        noise = rng.normal(0, 3, count) + 1j * rng.normal(0, 3, count)

        def encode(values):
            raw = np.empty(count * 2, dtype=np.int8)
            raw[0::2] = np.clip(values.real, -128, 127).astype(np.int8)
            raw[1::2] = np.clip(values.imag, -128, 127).astype(np.int8)
            return raw.tobytes()

        tone_level = source.measure(encode(tone + noise))
        noise_level = source.measure(encode(noise))
        self.assertGreater(tone_level - noise_level, 15)

    def test_center_dc_spike_is_rejected(self):
        source = self.make_source()
        count = source.chunk_bytes // 2
        dc = np.empty(count * 2, dtype=np.int8)
        dc[0::2] = -12
        dc[1::2] = 9
        self.assertLess(source.measure(dc.tobytes()), -70)


class HackRFTriggerTests(unittest.TestCase):
    def make_config(self, contained=True):
        return {
            "radio": {"frequency_mhz": "122.700000"},
            "sdr": {"serial": "test-serial"},
            "audio": {
                "file": "/tmp/current.wav",
                "timeout_seconds": 45,
                "max_tx_seconds": 50,
            },
            "transmission": {
                "method": "hackrf",
                "script": "/tmp/hackrf_transmit_once.py",
                "sample_rate": 2_000_000,
                "tx_gain_db": 0,
                "modulation_index": 0.75,
                "carrier_scale": 0.5,
                "device_settle_seconds": 0,
            },
            "safety": {
                "transmit_enabled": True,
                "contained_rf_confirmed": contained,
            },
        }

    @patch.object(click.subprocess, "run")
    def test_hackrf_trigger_stops_tx_then_restarts_receive(self, run_mock):
        source = Mock()
        transmitter = click.Transmitter(self.make_config(), logging.getLogger("test"), False)

        restarted = transmitter.trigger(source)

        self.assertTrue(restarted)
        source.stop.assert_called_once_with()
        source.start.assert_called_once_with()
        command = run_mock.call_args.args[0]
        self.assertIn("--transmit", command)
        self.assertIn("--confirm-contained-rf", command)
        self.assertEqual(run_mock.call_args.kwargs["timeout"], 50)

    @patch.object(click.subprocess, "run", side_effect=click.subprocess.TimeoutExpired("tx", 50))
    def test_receive_restarts_after_transmit_timeout(self, _run_mock):
        source = Mock()
        transmitter = click.Transmitter(self.make_config(), logging.getLogger("test"), False)

        transmitter.trigger(source)

        source.start.assert_called_once_with()

    def test_containment_gate_blocks_transmit_before_stopping_receive(self):
        source = Mock()
        transmitter = click.Transmitter(self.make_config(contained=False), logging.getLogger("test"), False)

        with self.assertRaisesRegex(RuntimeError, "contained_rf_confirmed"):
            transmitter.trigger(source)

        source.stop.assert_not_called()


class RadioRelayTriggerTests(unittest.TestCase):
    @patch.object(click.subprocess, "run")
    def test_radio_transmit_keys_relay_plays_audio_and_restarts_receiver(self, run_mock):
        config = {
            "radio": {"frequency_mhz": "122.700000"},
            "sdr": {},
            "audio": {
                "file": "/tmp/current.wav",
                "device": "plughw:CARD=Device,DEV=0",
                "ptt_lead_seconds": 0,
                "ptt_tail_seconds": 0,
                "timeout_seconds": 45,
                "max_tx_seconds": 50,
            },
            "transmission": {"method": "ptt_audio", "stop_receiver_during_tx": True, "receiver_settle_seconds": 0},
            "ptt": {"method": "usb_relay"},
            "safety": {"transmit_enabled": True},
        }
        source = Mock()
        transmitter = click.Transmitter(config, logging.getLogger("test"), False)
        transmitter.ptt = Mock()

        self.assertTrue(transmitter.trigger(source))

        self.assertEqual([call.args[0] for call in transmitter.ptt.call_args_list], [True, False])
        source.stop.assert_called_once_with()
        source.start.assert_called_once_with()
        self.assertEqual(
            run_mock.call_args.args[0],
            ["aplay", "-D", "plughw:CARD=Device,DEV=0", "/tmp/current.wav"],
        )


if __name__ == "__main__":
    unittest.main()
