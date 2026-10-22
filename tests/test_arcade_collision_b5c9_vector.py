"""ROM-free tests for recovered original B5C9-B63B correction-vector model.

Private original 524,288-case machine-code parity is a separate verifier;
this test never bundles original ROM bytes or proprietary contact payloads.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_b5c9_vector import (
    START, STOP, asr16, independent_vector, original_b5c9_opcodes,
    signed8, signed16, trig8, xrom_slot0_signed, verify,
)


class OriginalContactVectorTests(unittest.TestCase):
    def test_original_stage_boundaries(self):
        self.assertEqual((START, STOP), (0xB5C9, 0xB63C))
        self.assertEqual(STOP - START, 115)

    def test_independently_derived_integer_examples(self):
        observed = {
            (0, 0, 0): (0, 0),
            (1, 0, 0): (65531, 0),
            (17, 0, 0): (65466, 13),
            (127, 0, 0): (65020, 99),
            (127, 127, 240): (511, 87),
            (47, 30, 16): (65302, 65465),
            (96, 209, 128): (65002, 1017),
        }
        for args, values in observed.items():
            with self.subTest(args=args):
                self.assertEqual(independent_vector(*args), values)

    def test_original_signed_multiplication_and_rounding(self):
        self.assertEqual(signed8(128), -128)
        self.assertEqual(signed16(0xFFFF), -1)
        self.assertEqual(xrom_slot0_signed(128, 128), 32767)
        self.assertEqual(xrom_slot0_signed(128, 127), 0x8100)
        self.assertEqual(asr16(0xFFFF, 4), 0xFFFF)
        self.assertEqual(asr16(0xFFF1, 4), 0xFFFF)
        self.assertEqual(asr16(0x0011, 4), 1)
        self.assertEqual(trig8(0), 127)
        self.assertEqual(trig8(64), 0)
        self.assertEqual(trig8(128), 128)

    def test_zero_payload_is_zero_displacement(self):
        for heading in range(256):
            for quant in range(0, 256, 16):
                self.assertEqual(independent_vector(0, heading, quant), (0, 0))

    def test_validation_rejects_non_arcade_inputs(self):
        for args in ((128, 0, 0), (-1, 0, 0), (1, 256, 0), (1, 0, 1)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    independent_vector(*args)
        with self.assertRaisesRegex(ValueError, "original 1991 arcade master"):
            verify(bytes(0x90000), bytes(0x40000))
        with self.assertRaisesRegex(ValueError, "Unexpected original contact opcode"):
            original_b5c9_opcodes(bytes(0x90000), bytes(0x40000), 7, 1, 16)


if __name__ == "__main__":
    unittest.main()
