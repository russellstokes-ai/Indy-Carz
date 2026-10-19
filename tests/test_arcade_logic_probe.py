"""ROM-free regression checks for original arcade input recovery.

Full logic trace and game physics are NOT covered by these synthetic tests.
"""
import hashlib
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from arcade_logic_probe import (
    far_calls, game_steering_input, mame_dial_encode, steering_table,
)


class ArcadeInputRecoveryTests(unittest.TestCase):
    def test_original_response_signature_and_far_trampoline(self):
        fake = bytearray(0x90000)
        fake[0x0D6A:0x0D70] = bytes.fromhex("95 e6 1f 21 cd 0d")
        fake[0x0DCD:0x0DED] = bytes(range(32))
        fake[0x112C:0x1131] = bytes.fromhex("cd 5f 14 12 20")
        self.assertEqual(steering_table(fake), list(range(32)))
        calls = far_calls(fake)
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]["bank"], calls[0]["target"],
                          calls[0]["resume"]), (2, "2012", "1131"))

    def test_refuse_wrong_binary(self):
        with self.assertRaisesRegex(ValueError, "signature"):
            steering_table(bytes(0x90000))

    def test_mame_dial_directions_and_wrap(self):
        self.assertEqual(mame_dial_encode(1, 0, 0), 0x01)
        self.assertEqual(mame_dial_encode(0, 1, 0x01), 0x82)
        self.assertEqual(mame_dial_encode(0, 0, 0x82), 0x82)
        self.assertEqual(mame_dial_encode(0, 255, 0), 0x01)
        self.assertEqual(mame_dial_encode(255, 0, 0), 0x81)
        self.assertEqual(mame_dial_encode(120, 0, 0), 0x1F)

    def test_game_response_sign_and_phase(self):
        synthetic = [0, 12, 20, 26] + [62] * 28
        self.assertEqual(game_steering_input(0x01, 0, synthetic), (1, -12))
        self.assertEqual(game_steering_input(0x82, 1, synthetic), (2, 12))
        self.assertEqual(game_steering_input(0x80, 0, synthetic), (0, 0))
        self.assertEqual(game_steering_input(0x9F, 0, synthetic), (31, 62))

    def test_godot_response_matches_verified_rom_digest(self):
        source = (ROOT / "scripts/mechanics/ArcadeWheelInput.gd").read_text()
        values = source.split("const STEERING_RESPONSE :=", 1)[1]
        values = values.split("[", 1)[1].split("]", 1)[0]
        response = [int(n) for n in re.findall(r"\\d+", values)]
        self.assertEqual(len(response), 32)
        self.assertEqual(hashlib.sha256(bytes(response)).hexdigest(),
                         "ae7455b49967eaec332b4495bc01a7f6eeab9e360ed8ddcdf6229d3c397866b3")


if __name__ == "__main__":
    unittest.main()
