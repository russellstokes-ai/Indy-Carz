"""ROM-free original Z80 7442 signed double-XROM steering tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_7442_signed_projection import (
    START,STOP,SKIP,STAGE_SHA,independent,original_opcodes,product_word,verify
)

class Steering7442Tests(unittest.TestCase):
    def test_exact_original_source(self):
        self.assertEqual((START,STOP,SKIP),(0x7442,0x7463,0x748A))
        self.assertEqual(len(STAGE_SHA),64)

    def test_synthetic_golden_output_from_original_machine(self):
        cases=(
            ((64,0,0,0),0,0x7463,0x0040,0),
            ((64,0,0,1),0,0x748A,0x0040,0),
            ((32,127,127,0),3937,0x7463,0x7F20,0x1F7F),
            ((127,128,255,0),254,0x7463,0x807F,0x027F),
            ((32,255,128,1),65408,0x748A,0xFF20,0xFE40),
            ((127,255,255,0),65282,0x7463,0xFF7F,0xFE7F),
            ((64,128,128,0),57344,0x7463,0x8040,0x8040),
            ((127,127,127,255),16002,0x748A,0x7F7F,0x7E7F))
        for inputs,word,pc,first,second in cases:
            actual=independent(*inputs)
            self.assertEqual(
                (actual["correction"],actual["next_pc"],
                 actual["first_xrom_address"],actual["second_xrom_address"]),
                (word,pc,first,second))

    def test_indexed_bit_zero_selects_original_limiter(self):
        for b1 in range(256):
            result=independent(64,127,128,b1)
            self.assertEqual(result["next_pc"],SKIP if b1&1 else STOP)
            self.assertEqual(result["skip_velocity_limiter"],bool(b1&1))

    def test_weighted_negative_shifts_first_high_byte_and_second_factor(self):
        positive=independent(127,127,127,0)
        negative=independent(127,127,128,0)
        self.assertEqual(positive["first_xrom_address"],
                         negative["first_xrom_address"])
        self.assertNotEqual(positive["second_xrom_address"],
                            negative["second_xrom_address"])

    def test_exact_original_signed_multiply_saturation(self):
        self.assertEqual(product_word(127,127),0x7E02)
        self.assertEqual(product_word(128,128),0x7FFF)
        self.assertEqual(product_word(128,127),0x8100)
        self.assertEqual(product_word(0,255),0)

    def test_full_weighted_byte_domain_with_varied_control(self):
        for weighted in range(256):
            for control in (32,64,127):
                for car in (0,127,128,255):
                    result=independent(control,car,weighted,0)
                    self.assertTrue(0<=result["correction"]<65536)
                    self.assertTrue(0<=result["second_xrom_address"]<65536)

    def test_private_original_rom_and_input_checks(self):
        for args in ((31,0,0,0),(128,0,0,0),
                     (64,256,0,0),(64,0,256,0),(64,0,0,256)):
            with self.assertRaises(ValueError):independent(*args)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(10),bytes(10),64,0,0,0)
        with self.assertRaisesRegex(ValueError,"Authentic original"):
            verify(bytes(0x90000),bytes(0x40000),0)


if __name__=="__main__":unittest.main()
