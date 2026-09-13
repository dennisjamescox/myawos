import importlib.util
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
