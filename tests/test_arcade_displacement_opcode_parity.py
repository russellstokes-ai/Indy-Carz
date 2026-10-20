"""ROM-free regression checks for one recovered arcade displacement stage."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_displacement_opcode_parity import (
    MASTER_LEN, XROM_LEN, formula, original_z80_stage,
)


class DisplacementStageTests(unittest.TestCase):
    def test_exact_boundary_cases(self):
        examples = {
            (0, 0, 0): 0,
            (16, 16, 0): 0x20,
            (255, 255, 0): 0x0FC0,
            (255, 255, 128): 0xF040,
            (128, 200, 0): 0x0C80,
            (128, 200, 128): 0xF380,
        }
        for values, expected in examples.items():
            self.assertEqual(formula(*values), expected)

    def test_sign_reversal(self):
        for left in (0, 1, 64, 128, 255):
            for right in (0, 1, 64, 128, 255):
                pos = formula(left, right, 0)
                self.assertEqual(formula(left, right, 0x80), -pos & 0xFFFF)
                self.assertEqual(formula(left, right, 0xFF), -pos & 0xFFFF)

    def test_refuse_invalid_operand(self):
        with self.assertRaises(ValueError):
            formula(256, 1, 0)
        with self.assertRaises(ValueError):
            formula(10, -1, 0)

    def test_original_decoder_rejects_unknown_bytes(self):
        with self.assertRaisesRegex(ValueError, "Unsupported opcode"):
            original_z80_stage(bytes(MASTER_LEN), bytes(XROM_LEN), 1, 1, 0)


if __name__ == "__main__":
    unittest.main()
