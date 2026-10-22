"""ROM-free tests of the real original 7D4C short-position override."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from arcade_drive_7d4c_direct import independent, original_opcodes, verify_original


class Original7D4CDirectTests(unittest.TestCase):
    def test_direct_position_replaces_both_centres_then_returns_to_7024(self):
        actual = independent(3, 0x78, 0x56, 0x34, 0x12, 0xAAAA, 0xBBBB)
        self.assertEqual((actual["branch"], actual["y"], actual["x"], actual["next_pc"]),
                         ("direct_7024", 0x5678, 0x1234, 0x7024))

    def test_bit1_clear_does_not_guess_unknown_smoothing_path(self):
        actual = independent(1, 0x78, 0x56, 0x34, 0x12, 0xAAAA, 0xBBBB)
        self.assertEqual((actual["branch"], actual["y"], actual["x"], actual["next_pc"]),
                         ("slow_7d65", 0xAAAA, 0xBBBB, 0x7D65))

    def test_synthetic_data_is_not_the_original_rom(self):
        with self.assertRaises(ValueError):
            independent(256, 0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            independent(0, 0, 0, 0, 0, 65536, 0)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(1), 0, 0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            verify_original(bytes(0x90000), 1)


if __name__ == "__main__":
    unittest.main()
