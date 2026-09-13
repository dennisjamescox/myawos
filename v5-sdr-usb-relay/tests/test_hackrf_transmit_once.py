import importlib.util
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "hackrf_transmit_once.py"
SPEC = importlib.util.spec_from_file_location("hackrf_transmit_once", MODULE_PATH)
tx = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(tx)


class AMGenerationTests(unittest.TestCase):
    def test_generates_interleaved_iq_with_zero_q(self):
        audio = np.array([-1.0, 0.0, 1.0], dtype=np.float32)
        raw = b"".join(tx.iq_chunks(audio, 8_000, 2_000_000, 0.75, 0.5))
        iq = np.frombuffer(raw, dtype=np.int8)
        self.assertEqual(len(iq), 2 * 2 * 250)
        self.assertTrue(np.all(iq[1::2] == 0))
        self.assertGreaterEqual(int(iq[0::2].min()), 0)
        self.assertLessEqual(int(iq[0::2].max()), 127)

    def test_rejects_overmodulation(self):
        with self.assertRaises(ValueError):
            next(tx.iq_chunks(np.array([0.0, 1.0]), 8_000, 2_000_000, 1.1, 0.5))


if __name__ == "__main__":
    unittest.main()
