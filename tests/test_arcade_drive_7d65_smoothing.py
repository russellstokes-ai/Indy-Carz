"""Original-ROM-free tests of the special 7D65 five-word smoothing branch."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from arcade_drive_7d65_smoothing import independent, original_opcodes, verify_original


class Original7D65SmoothingTests(unittest.TestCase):
    def test_equal_centres_and_zero_velocity_return_to_caller(self):
        result = independent(0x1000, 0x2000, 0x1000, 0x2000,
                             0x30, 0x3000, 0xAAAA, 0, 0)
        self.assertEqual(result,
            {"branch": "smooth_7024", "next_pc": 0x7024,
             "y": 0x1000, "x": 0x2000, "e767": 0x3000,
             "e769": 0x3000, "e76b": 0, "e765": 0})

    def test_signed_centres_and_original_angle_speed_decay(self):
        result = independent(0x1010, 0x1FF0, 0x1000, 0x2000,
                             0x20, 0x1000, 0x9999, 0x0200, 0x1000)
        self.assertEqual(result,
            {"branch": "smooth_7024", "next_pc": 0x7024,
             "y": 0x1002, "x": 0x1FFE, "e767": 0x1180,
             "e769": 0x1180, "e76b": 0x01D0, "e765": 0x0E80})

    def test_wrapping_16bit_coordinates_are_not_float_interpolation(self):
        result = independent(0x0003, 0xFFFD, 0xFFFE, 0x0002,
                             0xFF, 0xFF00, 0, 0xFFFF, 0x0001)
        self.assertEqual(result["next_pc"], 0x7024)
        self.assertTrue(all(0 <= result[key] <= 0xFFFF for key in
                            ("y", "x", "e767", "e769", "e76b", "e765")))
        self.assertEqual(result["e767"], result["e769"])

    def test_unauthenticated_bytes_and_out_of_range_values_fail(self):
        with self.assertRaises(ValueError):
            independent(65536, 0, 0, 0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            independent(0, 0, 0, 0, 256, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000), *(0 for _ in range(9)))
        with self.assertRaises(ValueError):
            verify_original(bytes(0x90000), 1)


if __name__ == "__main__":
    unittest.main()
