"""ROM-free regression for original bank4 22BA X-ROM position metric."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_bank4_metric_22ba import (
    START,STOP,STAGE_SHA,independent,xrom_rounded_u8,original_opcodes,verify,
)


class OriginalBank4MetricTests(unittest.TestCase):
    def test_exact_original_routine_bounds(self):
        self.assertEqual((START,STOP),(0x22BA,0x2305))
        self.assertEqual(len(STAGE_SHA),64)

    def test_first_16bit_borrow_returns_original_de(self):
        actual=independent(255,255,2,0,127,80)
        self.assertEqual(actual,{"path":"early_no_room","hl":65535})

    def test_zero_metric_and_no_collision_with_base(self):
        self.assertEqual(independent(0,0,2,1,255,80),
                         {"path":"computed","hl":0,"fraction":0,
                          "first":0,"second":0})

    def test_original_two_bit_divide_and_two_stage_rounding(self):
        result=independent(1,0,2,3,64,80)
        self.assertEqual(result,{
            "path":"computed","hl":336,
            "fraction":128,"first":64,"second":20,
        })

    def test_original_four_bit_divide_and_two_stage_rounding(self):
        result=independent(0,0,4,4,64,80)
        self.assertEqual(result,{
            "path":"computed","hl":40,
            "fraction":64,"first":32,"second":10,
        })

    def test_original_clamp_to_255_fraction(self):
        result=independent(0,0,2,4,127,80)
        self.assertEqual(result["path"],"computed")
        self.assertEqual(result["fraction"],255)
        self.assertEqual(result["first"],253)
        self.assertEqual(result["second"],79)
        self.assertEqual(result["hl"],316)

    def test_car_parameter_doubles_in_eight_bit_domain(self):
        # Both original factors 0 and 128 produce zero after 8-bit shift.
        for original in (0,128):
            result=independent(0,0,2,4,original,255)
            self.assertEqual(result["first"],0)
            self.assertEqual(result["hl"],0)

    def test_second_original_factor_zero_cancels_adjustment(self):
        result=independent(0,25,4,4,63,0)
        self.assertEqual(result["second"],0)
        self.assertEqual(result["hl"],25)

    def test_xrom_rounded_fixed_point_boundaries(self):
        self.assertEqual(xrom_rounded_u8(255,255),254)
        self.assertEqual(xrom_rounded_u8(128,128),64)
        self.assertEqual(xrom_rounded_u8(127,127),63)
        self.assertEqual(xrom_rounded_u8(0,255),0)

    def test_invalid_original_input_or_unknown_divider_rejected(self):
        for args in ((-1,0,2,0,0,0),(256,0,2,0,0,0),
                     (0,0,0,0,0,0),(0,0,3,0,0,0),(0,0,2,256,0,0)):
            with self.assertRaises(ValueError):independent(*args)
        with self.assertRaises(ValueError):xrom_rounded_u8(-1,255)

    def test_untrusted_rom_refused_without_original_z80_data(self):
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000),bytes(0x40000),0,0,2,4,127,80)
        with self.assertRaisesRegex(ValueError,"authenticated master"):
            verify(bytes(0x90000),bytes(0x40000),0)


if __name__=="__main__":
    unittest.main()
