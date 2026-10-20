"""Synthetic-only checks for arcade input extraction (no original ROM required)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_input_extraction import (
    CAR_BASES, INPUT_SITES, extract, pedal_output, pedal_sample, wheel_response,
)


class ArcadeInputExtractionTests(unittest.TestCase):
    def test_car_state_stride(self):
        self.assertEqual(CAR_BASES, (0xE080, 0xE180, 0xE280, 0xE380, 0xE480))
        self.assertEqual(len(INPUT_SITES), 13)

    def test_counter_wrap_and_direction(self):
        wheel_curve = bytes([
            0, 12, 20, 26, 30, 32, 34, 36,
            36, 38, 40, 40, 42, 44, 44, 46,
            48, 48, 50, 52, 52, 54, 56, 56,
            58, 60, 60, 62, 62, 62, 62, 62
        ])
        self.assertEqual(wheel_response(0x01, 0x00, wheel_curve), -12)
        self.assertEqual(wheel_response(0x81, 0x00, wheel_curve), 12)
        self.assertEqual(wheel_response(0x01, 0x1F, wheel_curve), -20)
        self.assertEqual(wheel_response(0x80, 0x00, wheel_curve), 0)
        with self.assertRaises(ValueError):
            wheel_response(0, 0, b"x")

    def test_pedal_saturation_logic(self):
        self.assertEqual(pedal_output(255, 0), 0)
        self.assertEqual(pedal_output(255, 1), 0)
        self.assertEqual(pedal_output(240, 32), 32)
        self.assertEqual(pedal_output(255, 64), 126)
        self.assertEqual(pedal_output(255, 65), 126)
        self.assertEqual(pedal_output(129, 128), 2)

    def test_pedal_xrom_slot_and_address(self):
        xrom = bytearray(0x40000)
        xrom[0x10000 | (0xA5 << 8) | 0x12] = 240
        self.assertEqual(pedal_sample(xrom, 0xA5, 0x12, 32), 32)
        self.assertEqual(pedal_sample(xrom, 0xA5, 0x13, 32), 0)

    def test_wrong_rom_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA256"):
            extract(bytes(0x90000), bytes(0x40000))


if __name__ == "__main__":
    unittest.main()
