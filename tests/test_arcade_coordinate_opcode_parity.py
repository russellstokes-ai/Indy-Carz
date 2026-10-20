"""ROM-free regression tests for original trigonometric coordinate model."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_coordinate_opcode_parity import (
    arcade_trig, axis_step, independent_model, signed8, verify,
)


class OriginalTrigonometricStageTests(unittest.TestCase):
    def test_exact_quadrant_trig_samples(self):
        self.assertEqual([arcade_trig(a, False) for a in (0, 64, 128, 192)],
                         [127, 0, -128, 0])
        self.assertEqual([arcade_trig(a, True) for a in (0, 64, 128, 192)],
                         [0, 127, 0, -128])
        self.assertEqual((arcade_trig(32, False), arcade_trig(32, True)), (91, 91))
        self.assertEqual((arcade_trig(1, False), arcade_trig(1, True)), (127, 3))

    def test_original_byte_to_signed_conversion(self):
        self.assertEqual(signed8(0), 0)
        self.assertEqual(signed8(127), 127)
        self.assertEqual(signed8(128), -128)
        self.assertEqual(signed8(255), -1)

    def test_bounded_coordinate_examples(self):
        self.assertEqual(independent_model(0, 64, 32768, 32768),
                         (32768, 33022))
        self.assertEqual(independent_model(64, 64, 32768, 32768),
                         (33022, 32768))
        self.assertEqual(independent_model(128, 64, 32768, 32768),
                         (32768, 32512))
        self.assertEqual(independent_model(192, 64, 32768, 32768),
                         (32512, 32768))
        self.assertEqual(independent_model(255, 128, 65535, 65535),
                         (11, 65027))

    def test_integer_saturation_and_rounding(self):
        self.assertEqual(axis_step(-128, -128), 512)
        self.assertEqual(axis_step(-128, 127), -508)
        self.assertEqual(axis_step(127, 127), 504)
        self.assertEqual(axis_step(1, 1), 0)
        self.assertEqual(axis_step(32, -2), -2)

    def test_input_rejected_and_private_image_gate(self):
        with self.assertRaises(ValueError):
            arcade_trig(256, True)
        with self.assertRaises(ValueError):
            independent_model(32, 300, 0, 0)
        with self.assertRaisesRegex(ValueError, "master arcade"):
            verify(bytes(0x90000), bytes(0x40000))


if __name__ == "__main__":
    unittest.main()
