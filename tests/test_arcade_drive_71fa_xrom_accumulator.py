"""ROM-free tests for original Z80 71FA signed-XROM accumulator and escape."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_71fa_xrom_accumulator import (
    START,STOP,EXTERNAL,STAGE_SHA,signed_xrom_word,
    independent,original_opcodes,verify
)


class OriginalSignedXromAccumulatorTests(unittest.TestCase):
    def test_original_bounded_stage_and_unverified_external(self):
        self.assertEqual((START,STOP,EXTERNAL),(0x71FA,0x7225,0x1689))
        self.assertEqual(len(STAGE_SHA),64)

    def test_original_c_zero_entire_lookup_skipped(self):
        for e933 in (0,1,0x7FFF,0xFFFF):
            for de in (0,1,0x8000,0xFFFF):
                r=independent(0,e933,de)
                self.assertEqual(r,{"exit":"skip_C_zero","next_pc":STOP,
                                    "de":de,"xr_addresses":()})

    def test_original_known_nonzero_xrom_case(self):
        r=independent(1,0x1234,0)
        self.assertEqual(r["exit"],"normal_7225")
        self.assertEqual(r["de"],0x0012)
        self.assertEqual(r["xr_addresses"],(0x1201,0x1A01))

    def test_original_overflow_does_not_forge_later_motion(self):
        r=independent(1,0x1234,0x7FFF)
        self.assertEqual(r["exit"],"external_1689")
        self.assertEqual(r["next_pc"],EXTERNAL)
        self.assertIsNone(r["de"])

    def test_two_distinct_original_xrom_addresses(self):
        r=independent(255,0xA5FD,0)
        self.assertEqual(r["xr_addresses"],(0xA5FF,0x7EFF))

    def test_original_signed_double_product_saturation(self):
        self.assertEqual(signed_xrom_word(127,127),0x7E02)
        self.assertEqual(signed_xrom_word(128,128),0x7FFF)
        self.assertEqual(signed_xrom_word(128,127),0x8100)
        self.assertEqual(signed_xrom_word(0,255),0)

    def test_complete_signed_8bit_multiply_ranges(self):
        for a in range(256):
            for b in (0,1,127,128,255):
                reference=((a-256 if a&128 else a)*
                           (b-256 if b&128 else b)*2)
                reference=min(32767,max(-32768,reference))&0xFFFF
                self.assertEqual(signed_xrom_word(a,b),reference)

    def test_continuation_no_external_path_when_no_overflow(self):
        for de in (0,1,255,0x7FFF):
            r=independent(1,0x0000,de)
            self.assertEqual(r["exit"],"normal_7225")
            self.assertEqual(r["de"],de)

    def test_rounded_16bit_output_not_unbounded_signed_addition(self):
        r=independent(1,0x1234,0xFFFF)
        self.assertIn(r["exit"],("normal_7225","external_1689"))
        self.assertTrue(r["de"] is None or 0<=r["de"]<=65535)

    def test_unsupported_fields_and_private_rom_required(self):
        for args in ((256,0,0),(-1,0,0),(0,-1,0),
                     (0,65536,0),(0,0,65536)):
            with self.assertRaises(ValueError):independent(*args)
        for args in ((-1,0),(256,0),(0,-1),(0,256)):
            with self.assertRaises(ValueError):signed_xrom_word(*args)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(10),bytes(2),1,0,0)
        with self.assertRaisesRegex(ValueError,"Authentic original master"):
            verify(bytes(0x90000),bytes(0x40000),0)


if __name__=="__main__":
    unittest.main()
