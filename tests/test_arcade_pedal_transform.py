"""Regression of original arcade pedal transform (no proprietary ROM)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from arcade_pedal_opcode_parity import pedal_formula


class OriginalPedalInputTests(unittest.TestCase):
    def test_8bit_fixed_point_product_and_threshold(self):
        self.assertEqual(pedal_formula(0, 255, 255), 0)
        self.assertEqual(pedal_formula(2, 255, 255), 2)
        self.assertEqual(pedal_formula(16, 64, 254), 4)
        self.assertEqual(pedal_formula(255, 255, 255), 126)

    def test_output_is_even_saturated_and_never_negative(self):
        for raw in range(256):
            for factor in (0, 1, 64, 127, 128, 192, 255):
                for bias in (0, 127, 192, 253, 254, 255):
                    response = pedal_formula(raw, factor, bias)
                    self.assertGreaterEqual(response, 0)
                    self.assertLessEqual(response, 126)
                    self.assertEqual(response % 2, 0)

    def test_godot_port_contains_original_fixed_point_calculation(self):
        gd = (ROOT / "scripts/mechanics/ArcadePedalInput.gd").read_text()
        self.assertIn("(pedal_raw * car_factor) + 128", gd)
        self.assertIn("offset_sum >= 256", gd)
        self.assertIn("RESPONSE_MAX", gd)
        self.assertIn("0x7E", gd)


if __name__ == "__main__":
    unittest.main()
