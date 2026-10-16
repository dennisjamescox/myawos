import importlib.util
import json
import logging
import tempfile
import unittest
import wave
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "radio_audio.py"
SPEC = importlib.util.spec_from_file_location("radio_audio", MODULE_PATH)
audio = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audio)


class RadioAudioCaptureTests(unittest.TestCase):
    def test_capture_writes_audio_and_configured_aircraft_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = {
                "enabled": True,
                "live_enabled": False,
                "directory": temporary,
                "pre_roll_seconds": 0,
                "tail_seconds": 0.1,
                "minimum_active_seconds": 0.1,
            }
            capture = audio.RadioAudioCapture(config, 1000, "122.700000", logging.getLogger("test"))
            context = [{"registration": "N12345", "distance_nm": 2.5}]
            capture.ingest(b"\x01\x00" * 200, True, recording_context=context)
            capture.ingest(b"\x00\x00" * 100, False)

            files = list(Path(temporary).glob("*/*.wav"))
            self.assertEqual(len(files), 1)
            with wave.open(str(files[0]), "rb") as recorded:
                self.assertEqual(recorded.getframerate(), 1000)
            metadata = json.loads(files[0].with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["owned_aircraft_gate"][0]["registration"], "N12345")
            capture.close()


if __name__ == "__main__":
    unittest.main()
