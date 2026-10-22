"""ROM-free guardrails for the original arcade 709C–7123 speed stage."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from arcade_drive_709c_speed import (
    START, STOP, independent, original_opcodes, slot0_word, slot1_low,
    verify_original,
)


class OriginalDrive709CSpeedTests(unittest.TestCase):
    def setUp(self):
        self.table = bytes(256)

    def calculate(self, b=0, e765=0, ix54=0, ix3c=0, ix60=0, ix61=0, table=None):
        return independent(
            b, e765, ix54, ix3c, ix60, ix61,
            self.table if table is None else table,
        )

    def test_bounded_original_pc_and_xrom_math(self):
        self.assertEqual((START, STOP), (0x709C, 0x7124))
        self.assertEqual(slot1_low(255, 255), 254)
        self.assertEqual(slot1_low(0, 255), 0)
        self.assertEqual(slot0_word(128, 128), 0x7FFF)
        self.assertEqual(slot0_word(128, 127), 0x8100)

    def test_equal_branch_skips_the_rom_source_and_preserves_motion(self):
        result = self.calculate(b=0, e765=0, ix54=0)
        self.assertEqual((result["branch"], result["e765"], result["next_pc"]),
                         ("equal", 0, STOP))

    def test_lower_input_can_trigger_original_zero_clamp(self):
        result = self.calculate(b=0, e765=0xFF00)
        self.assertEqual((result["branch"], result["e765"]), ("subtract", 0))

    def test_higher_input_uses_original_positive_branch(self):
        result = self.calculate(b=255, e765=0, ix54=255)
        self.assertEqual((result["branch"], result["b"], result["e765"]),
                         ("add", 255, 0))

    def test_positive_addition_uses_saturated_signed_slot0(self):
        table = bytearray(256)
        table[0] = 127
        result = self.calculate(b=255, e765=0x7F00, ix60=10,
                                table=bytes(table))
        self.assertEqual(result["branch"], "add")
        self.assertEqual(result["e765"], 0x7FFF)

    def test_256_looking_table_values_are_not_built_in_constants(self):
        table = bytes(range(256))
        result = self.calculate(b=128, e765=0x3000, ix54=15,
                                ix3c=0x55, ix60=0x40, ix61=0x80,
                                table=table)
        self.assertEqual(result["factor"], table[(-0x55) & 255])
        self.assertIn(result["branch"], ("add", "subtract", "equal"))

    def test_inputs_require_actual_original_ranges_and_full_table(self):
        with self.assertRaises(ValueError):
            self.calculate(b=256)
        with self.assertRaises(ValueError):
            self.calculate(e765=-1)
        with self.assertRaises(ValueError):
            self.calculate(table=bytes(255))
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x100), 0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            verify_original(bytes(0x90000), 0)


if __name__ == "__main__":
    unittest.main()
