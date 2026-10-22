"""ROM-free tests of original 73CD signed input and double X-ROM steering."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_73cd_weighted_steering import (
    START,STOP,BASE,HELPER,STAGE_SHA,TABLE_SHA,HELPER_SHA,
    round8,table_index,independent,original_z80,verify
)


class OriginalWeightedSteering73CDTests(unittest.TestCase):
    def test_original_cpu_and_factor_page_ranges(self):
        self.assertEqual((START,STOP,BASE,HELPER),
                         (0x73CD,0x73F6,0x7635,0x1C85))
        self.assertTrue(all(len(x)==64 for x in
                            (STAGE_SHA,TABLE_SHA,HELPER_SHA)))

    def test_original_abs_motion_table_index_all_256_bytes(self):
        for raw in range(256):
            signed=raw if raw<128 else raw-256
            expected=(min(127,abs(signed))+1)//2
            self.assertEqual(table_index(raw),expected)
        self.assertEqual(max(table_index(i) for i in range(256)),64)

    def test_original_neg128_helper_is_returning_saturation(self):
        self.assertEqual(table_index(128),64)
        self.assertEqual(table_index(129),64)
        self.assertEqual(table_index(127),64)
        actual=independent(128,255,255,255)
        self.assertTrue(actual["neg128_saturated"])
        self.assertEqual(actual["next_pc"],STOP)
        self.assertEqual(actual["table_index"],64)

    def test_original_double_unsigned_rounding_not_float(self):
        original=independent(42,255,255,255)
        self.assertEqual(original["first_low"],254)
        self.assertEqual(original["weighted"],253)
        self.assertEqual(original["xr_addresses"],(0xFFFF,0xFFFE))

    def test_second_operand_is_exact_first_lookup_low_byte(self):
        for factor in (0,1,127,128,255):
            for b in (0,1,127,128,255):
                for car in (0,1,127,128,255):
                    result=independent(63,b,car,factor)
                    self.assertEqual(result["first_low"],round8(factor,b))
                    self.assertEqual(result["weighted"],round8(car,result["first_low"]))
                    self.assertEqual(result["xr_addresses"],
                        ((factor<<8)|b,(car<<8)|result["first_low"]))

    def test_original_signed_motion_symmetry_in_factor_index(self):
        for absolute in range(1,128):
            positive=table_index(absolute)
            negative=table_index(256-absolute)
            self.assertEqual(positive,negative)

    def test_zero_input_factor_or_B_yields_zero(self):
        for factor,b,car in ((0,255,255),(255,0,255),(0,0,0)):
            actual=independent(0,b,car,factor)
            self.assertEqual(actual["weighted"],0)
            self.assertEqual(actual["next_pc"],STOP)

    def test_exact_8bit_rounded_product_boundaries(self):
        self.assertEqual(round8(0,255),0)
        self.assertEqual(round8(255,255),254)
        self.assertEqual(round8(128,128),64)
        self.assertEqual(round8(127,127),63)

    def test_all_signed_motion_inputs_and_dense_factor_cases(self):
        for motion in range(256):
            for b in (0,1,64,127,128,254,255):
                for car in (0,1,127,128,255):
                    factor=(motion+b+car)&255
                    result=independent(motion,b,car,factor)
                    self.assertTrue(0<=result["weighted"]<=255)
                    self.assertTrue(0<=result["table_index"]<=64)

    def test_original_opcode_parser_rejects_untrusted_private_rom(self):
        with self.assertRaises(ValueError):
            original_z80(bytes(2),bytes(1),0,0,0)
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            verify(bytes(0x90000),bytes(0x40000),0)

    def test_invalid_original_byte_fields_fail_closed(self):
        for args in ((-1,0,0,0),(256,0,0,0),(0,256,0,0),
                     (0,0,-1,0),(0,0,0,256)):
            with self.assertRaises(ValueError):independent(*args)
        with self.assertRaises(ValueError):round8(-1,1)


if __name__=="__main__":
    unittest.main()
