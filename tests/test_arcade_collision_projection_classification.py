"""ROM-free synthetic regression tests for exact original B6ED projection."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_projection_classification import (
    START, STOP, TABLE_COUNT, signed8, trig8, xrom_hi_math,
    model, execute_original, verify,
)


class OriginalContactProjectionTests(unittest.TestCase):
    def test_original_stage_bounds_and_signed_byte_inputs(self):
        self.assertEqual((START, STOP), (0xB6ED, 0xB728))
        self.assertEqual(TABLE_COUNT, 24)
        self.assertEqual(signed8(255), -1)
        self.assertEqual(signed8(128), -128)

    def test_original_angle_cardinals(self):
        self.assertEqual(trig8(0, True), 127)
        self.assertEqual(trig8(64, False), 127)
        self.assertEqual(trig8(128, True), 128)
        self.assertEqual(trig8(192, False), 128)

    def test_original_signed_multiply_saturation(self):
        self.assertEqual(xrom_hi_math(127, 127), 126)
        self.assertEqual(xrom_hi_math(128, 128), 127)
        self.assertEqual(xrom_hi_math(128, 127), 129)

    def test_projection_threshold_and_low_branch(self):
        self.assertEqual(model(0, 0, 0, 0), (0, 1, "B778"))
        self.assertEqual(model(0, 0, 10, 0), (0, 10, "B728"))

    def test_negative_projection_branch(self):
        self.assertEqual(model(0, 0, 246, 0), (0, 247, "B86C"))

    def test_signed_saturation_both_directions(self):
        self.assertEqual(model(0, 32, 127, 127), (0, 127, "B728"))
        self.assertEqual(model(0, 32, 128, 128), (0, 128, "B86C"))

    def test_event_flags_and_angle_rotation(self):
        self.assertEqual(model(0xC3, 0, 10, 0), (3, 1, "B778"))
        for synthetic_byte in (0, 1, 3, 0x31, 0x40, 0x80, 0xC0, 0xF3):
            flags, projected, destination = model(synthetic_byte, 0, 1, 0)
            self.assertEqual(flags, synthetic_byte & 0x33)
            self.assertIn(destination, ("B728", "B778", "B86C"))
            self.assertTrue(0 <= projected <= 255)

    def test_invalid_inputs_and_missing_rom_fail_closed(self):
        for invalid in (-1, 256):
            for inputs in ((invalid, 0, 0, 0), (0, invalid, 0, 0),
                           (0, 0, invalid, 0), (0, 0, 0, invalid)):
                with self.assertRaises(ValueError):
                    model(*inputs)
        with self.assertRaises(ValueError):
            execute_original(bytes(0x90000), bytes(0x40000), 24, 0, 0, 0)
        with self.assertRaises(ValueError):
            execute_original(bytes(0x90000), bytes(0x40000), 0, 0, 0, 0)
        with self.assertRaisesRegex(ValueError, "Private original verified master"):
            verify(bytes(0x90000), bytes(0x40000), 0)


if __name__ == "__main__":
    unittest.main()
