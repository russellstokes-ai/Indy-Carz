"""ROM-free correctness checks for recovered original arcade X-ROM formulas."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_xrom_math import (
    analyze, signed8, signed_multiply_doubled,
    unsigned_multiply_rounded, slot0_word, slot1_low,
)


class XromArithmeticTests(unittest.TestCase):
    def test_signed_inputs(self):
        self.assertEqual(signed8(0), 0)
        self.assertEqual(signed8(127), 127)
        self.assertEqual(signed8(128), -128)
        self.assertEqual(signed8(255), -1)

    def test_signed_multiplication_and_saturation(self):
        self.assertEqual(signed_multiply_doubled(0, 255), 0)
        self.assertEqual(signed_multiply_doubled(1, 255), 0xFFFE)
        self.assertEqual(signed_multiply_doubled(255, 255), 2)
        self.assertEqual(signed_multiply_doubled(127, 127), 32258)
        self.assertEqual(signed_multiply_doubled(128, 128), 32767)
        self.assertEqual(signed_multiply_doubled(128, 127), 0x8100)

    def test_rounded_unsigned_multiplication(self):
        self.assertEqual(unsigned_multiply_rounded(0, 255), 0)
        self.assertEqual(unsigned_multiply_rounded(255, 255), 254)
        self.assertEqual(unsigned_multiply_rounded(128, 128), 64)
        self.assertEqual(unsigned_multiply_rounded(1, 128), 1)

    def test_byte_interleaving(self):
        image = bytearray(0x40000)
        image[2 * (0x31 << 8 | 0x44)] = 0xED
        image[2 * (0x31 << 8 | 0x44) + 1] = 0xBC
        image[0x20000 + 2 * (0x31 << 8 | 0x44)] = 0x7B
        self.assertEqual(slot0_word(image, 0x31, 0x44), 0xBCED)
        self.assertEqual(slot1_low(image, 0x31, 0x44), 0x7B)

    def test_input_gate(self):
        with self.assertRaisesRegex(ValueError, "original arcade"):
            analyze(bytes(0x40000))


if __name__ == "__main__":
    unittest.main()
