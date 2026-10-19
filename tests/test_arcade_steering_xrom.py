"""Synthetic X-ROM steering samples. No proprietary ROM required."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_steering_xrom import xrom_steering_sample


class SteeringXromTests(unittest.TestCase):
    def test_port_upper_byte_mapping_and_signed_double(self):
        rom = bytearray(0x40000)
        for signed, value in [(-12, 0xF4), (0, 0), (12, 0x0B), (62, 0x3D)]:
            address = (((signed & 255) << 8) | 0x7F)
            rom[address * 2 + 1] = value
        for signed, expected in [(-12, -24), (0, 0), (12, 22), (62, 122)]:
            self.assertEqual(xrom_steering_sample(rom, signed)["doubled_signed"],
                             expected)

    def test_reject_bad_xrom_size_or_steering_value(self):
        with self.assertRaisesRegex(ValueError, "0x40000"):
            xrom_steering_sample(bytes(20), 0)
        with self.assertRaisesRegex(ValueError, "signed 8-bit"):
            xrom_steering_sample(bytes(0x40000), 128)


if __name__ == "__main__":
    unittest.main()
