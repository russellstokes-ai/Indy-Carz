"""ROM-free original arcade fixed 1C8C regression checks."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_original_rng_1c8c import (
    START, STOP, independent, original_opcodes, verify,
)


class OriginalRNGTests(unittest.TestCase):
    def test_original_stage(self):
        self.assertEqual((START, STOP), (0x1C8C, 0x1CA2))

    def test_known_exact_original_seed(self):
        self.assertEqual(independent(0,0), (0x1D87, 0x9A))

    def test_z80_16bit_wrap_on_shift(self):
        self.assertEqual(independent(0,0),independent(0x8000,0))

    def test_refresh_register_changes_return(self):
        for state in (0,1,0x7FFF,0x8000,0xFFFF):
            self.assertNotEqual(independent(state,0),independent(state,1))

    def test_return_byte_high_xor_low(self):
        for state in (0,1,255,0xABCD,65535):
            for refresh in (0,1,127,128,255):
                updated,result=independent(state,refresh)
                self.assertEqual(result, (updated>>8) ^ (updated&255))

    def test_no_unverified_prng_input(self):
        for previous,refresh in ((-1,0),(65536,0),(0,-1),(0,256)):
            with self.assertRaises(ValueError):
                independent(previous,refresh)

    def test_fake_original_binary_is_not_accepted(self):
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000),0,0)
        with self.assertRaisesRegex(ValueError, "Checksum-verified"):
            verify(bytes(0x90000),0)


if __name__ == "__main__":
    unittest.main()
