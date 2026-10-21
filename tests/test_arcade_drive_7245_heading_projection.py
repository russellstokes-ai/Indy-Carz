"""ROM-free original heading-relative XROM motion stage regression tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_7245_heading_projection import (
    START,STOP,CODE_SHA,COS_SHA,cos_byte,slot0,
    independent,original_z80,verify,
)


class Original7245HeadingProjectionTests(unittest.TestCase):
    def test_exact_original_Z80_stage(self):
        self.assertEqual((START,STOP),(0x7245,0x726D))
        self.assertEqual(len(CODE_SHA),64)
        self.assertEqual(len(COS_SHA),64)

    def test_zero_motion_exact_original_arithmetic(self):
        self.assertEqual(independent(0,0,0),{
            "e933":0,"angle":0,"cosbyte":127,
            "first_xrom_address":0x007F,
            "second_xrom_address":0x007F,"next_pc":STOP})

    def test_original_quarter_turn_orthogonal_projection(self):
        r=independent(64,0,0x1234)
        self.assertEqual((r["angle"],r["cosbyte"],r["e933"]),(64,0,0))

    def test_max_positive_heading_projection(self):
        r=independent(0,0,0x7FFF)
        self.assertEqual((r["e933"],r["first_xrom_address"],
                          r["second_xrom_address"]),
                         (32510,32639,32639))

    def test_negative_word_with_wrapped_heading(self):
        r=independent(255,0xFFFF,0xFFFF)
        self.assertEqual((r["angle"],r["cosbyte"],r["e933"]),(0,127,65534))

    def test_180_degree_original_heading_diff(self):
        r=independent(128,0,0x8000)
        self.assertEqual(r["angle"],128)
        self.assertEqual(r["cosbyte"],128)
        self.assertTrue(0<=r["e933"]<=65535)

    def test_original_signed_XROM_exhaustive_boundary_arithmetic(self):
        self.assertEqual(slot0(127,127),0x7E02)
        self.assertEqual(slot0(128,128),0x7FFF)
        self.assertEqual(slot0(128,127),0x8100)
        for a in range(256):
            for b in (0,1,127,128,255):
                aa=a-256 if a>=128 else a
                bb=b-256 if b>=128 else b
                value=max(-32768,min(32767,aa*bb*2))&65535
                self.assertEqual(slot0(a,b),value)

    def test_every_heading_relative_cosine_input(self):
        self.assertEqual(cos_byte(0),127)
        self.assertEqual(cos_byte(64),0)
        self.assertEqual(cos_byte(128),128)
        self.assertEqual(cos_byte(192),0)
        self.assertEqual(len({cos_byte(n) for n in range(256)})>100,True)

    def test_exhaustive_small_motion_cases(self):
        for heading in range(256):
            for motion in (0,1,2,255,256,32767,32768,65535):
                result=independent(heading,0,motion)
                self.assertTrue(0<=result["e933"]<65536)
                self.assertTrue(0<=result["first_xrom_address"]<65536)
                self.assertTrue(0<=result["second_xrom_address"]<65536)

    def test_bad_fields_and_missing_private_rom_rejected(self):
        for args in ((-1,0,0),(256,0,0),(0,-1,0),
                     (0,65536,0),(0,0,-1),(0,0,65536)):
            with self.assertRaises(ValueError):independent(*args)
        with self.assertRaises(ValueError):slot0(-1,0)
        with self.assertRaises(ValueError):
            original_z80(bytes(0x90000),bytes(3),0,0,0)
        with self.assertRaisesRegex(ValueError,"[Cc]hecksum-verified"):
            verify(bytes(0x90000),bytes(0x40000),0)


if __name__=="__main__":
    unittest.main()
