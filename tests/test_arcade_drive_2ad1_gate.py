"""ROM-free tests of the genuine 2AD1 bit gate before banked event code."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from arcade_drive_2ad1_gate import independent, original_opcodes, verify_original


class Original2AD1GateTests(unittest.TestCase):
    def test_original_bit_zero_set_returns_to_709b_without_mutations(self):
        self.assertEqual(independent(1),
            {"branch": "return_709b", "next_pc": 0x709B, "complete": True})
        self.assertEqual(independent(0xFF)["next_pc"], 0x709B)

    def test_other_cars_stop_before_banked_event_data(self):
        self.assertEqual(independent(0),
            {"branch": "dispatch_2ad6", "next_pc": 0x2AD6, "complete": False})
        self.assertEqual(independent(0xFE)["next_pc"], 0x2AD6)

    def test_no_fabricated_rom_or_invalid_input(self):
        with self.assertRaises(ValueError):
            independent(256)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000), 0)
        with self.assertRaises(ValueError):
            verify_original(bytes(0x90000), 1)


if __name__ == "__main__":
    unittest.main()
