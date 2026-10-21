"""ROM-free exact original Z80 angular-motion update 72D3-7314 tests."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_72d3_angular_update import (
    START,STOP,EXTERNAL,STAGE_SHA,HELPER_SHA,FACTOR_SHA,
    signed16,slot0_word,independent,original_z80,verify
)

def synthetic(factor=127,car_field=42):
    memory=bytearray(0x90000)
    memory[0x2000+((-car_field)&255)]=factor
    return bytes(memory)

class OriginalAngular72D3Tests(unittest.TestCase):
    def test_original_bounds_helper_and_factor_page_hashes(self):
        self.assertEqual((START,STOP,EXTERNAL),(0x72D3,0x7315,0x1689))
        for value in (STAGE_SHA,HELPER_SHA,FACTOR_SHA):
            self.assertEqual(len(value),64)

    def test_zero_change_zero_original_motion(self):
        self.assertEqual(independent(synthetic(0),42,0,0),{
            "exit":"normal_7315","next_pc":STOP,"e765":0,"factor":0,
            "projection":0,"delta":0,"overflow_sub":False})

    def test_zero_factor_preserves_nonnegative_angle(self):
        for word in (0,1,0x2000,0x7FFF):
            result=independent(synthetic(0),42,12345,word)
            self.assertEqual(result["e765"],word)
            self.assertEqual(result["delta"],0)

    def test_original_signed_subtract_overflow_negative_clamp(self):
        result=independent(synthetic(1),42,0x1234,0x8000)
        self.assertEqual(result["exit"],"normal_7315")
        self.assertTrue(result["overflow_sub"])
        self.assertEqual(result["projection"],36)
        self.assertEqual(result["delta"],144)
        self.assertEqual(result["e765"],0)

    def test_original_signed_subtract_overflow_positive_limit(self):
        result=independent(synthetic(1),42,0x8000,0x7FFF)
        self.assertTrue(result["overflow_sub"])
        self.assertEqual(result["projection"],65280)
        self.assertEqual(result["delta"],64512)
        self.assertEqual(result["e765"],0x7FFF)

    def test_nonlocal_first_multiply_overflow(self):
        result=independent(synthetic(127),42,0x7FFF,0x1010)
        self.assertEqual(result["exit"],"external_1689_first_double")
        self.assertEqual(result["projection"],32510)
        self.assertEqual(result["next_pc"],EXTERNAL)
        self.assertEqual(result["e765"],0x1010)
        self.assertIsNone(result["delta"])

    def test_nonlocal_second_multiply_overflow(self):
        result=independent(synthetic(64),42,0x4000,0x2000)
        self.assertEqual(result["exit"],"external_1689_second_double")
        self.assertEqual(result["projection"],8192)
        self.assertEqual(result["next_pc"],EXTERNAL)
        self.assertEqual(result["e765"],0x2000)
        self.assertIsNone(result["delta"])

    def test_car_field_uses_original_neg_instruction_for_factor(self):
        memory=bytearray(0x90000)
        for i in range(256):memory[0x2000+i]=(i*23)&255
        for original_index in range(256):
            result=independent(bytes(memory),original_index,0,0)
            self.assertEqual(result["factor"],(((-original_index)&255)*23)&255)

    def test_original_slot0_signed_saturated_rounding(self):
        self.assertEqual(slot0_word(127,127),0x7E02)
        self.assertEqual(slot0_word(128,128),0x7FFF)
        self.assertEqual(slot0_word(128,127),0x8100)
        self.assertEqual(signed16(65535),-1)

    def test_synthetic_negative_angular_word_clamped_when_nonoverflow(self):
        result=independent(synthetic(0),42,0,0x8000)
        self.assertEqual(result["exit"],"normal_7315")
        self.assertFalse(result["overflow_sub"])
        self.assertEqual(result["e765"],0)

    def test_invalid_source_and_nonoriginal_opcodes_rejected(self):
        for args in ((-1,0,0),(256,0,0),(0,-1,0),
                     (0,65536,0),(0,0,65536)):
            with self.assertRaises(ValueError):independent(synthetic(),*args)
        with self.assertRaises(ValueError):
            original_z80(bytes(5),bytes(6),42,0,0)
        with self.assertRaisesRegex(ValueError,"authenticated original private master"):
            verify(bytes(0x90000),bytes(0x40000),0)

if __name__=="__main__":unittest.main()
