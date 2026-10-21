"""ROM-free original-Z80 71C8 drive-entry, signed displacement tests."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_71c8_entry import (
    START,STOP,STAGE_SHA,SHORT_CIRCUIT,independent,original_z80,verify
)


class DriveEntry71C8Tests(unittest.TestCase):
    def test_exact_original_cpu_stage_and_source_fingerprint(self):
        self.assertEqual((START,STOP,SHORT_CIRCUIT),(0x71C8,0x71FF,0x726D))
        self.assertEqual(len(STAGE_SHA),64)

    def test_high_pedal_response_and_c_zero_skips_all_motion(self):
        for response in (16,17,127,128,255):
            for b in (0,1,255):
                result=independent(response,b,0,255,255)
                self.assertEqual(result,{
                    "exit":"skip_direct_726D","next_pc":SHORT_CIRCUIT,
                    "de":None,"source":"car_response_ge_16_C_zero"})

    def test_high_pedal_response_and_c_nonzero_force_zero_de(self):
        for response in (16,128,255):
            for c in (1,2,127,128,255):
                result=independent(response,255,c,255,128)
                self.assertEqual(result["next_pc"],STOP)
                self.assertEqual(result["de"],0)
                self.assertEqual(result["exit"],"zero_contribution_71FF")

    def test_low_pedal_response_and_c_zero_still_clamps_velocity(self):
        result=independent(15,255,0,255,0)
        self.assertEqual(result["next_pc"],0x7225)
        self.assertEqual(result["exit"],"skip_xrom_7225")
        self.assertIsInstance(result["de"],int)

    def test_original_unsigned_8bit_rounded_product_displacement(self):
        # Round-to-nearest unsigned 8x8 product; double modulo 256,
        # shift by four; E76C bit7 reverses the original 16-bit sign.
        for b,f5 in ((0,255),(1,255),(255,1),(255,255),(128,255),
                     (127,255),(255,128),(200,200)):
            for sign in (0,127,128,255):
                product=((b*f5+128)>>8)
                raw=(((product<<1)&255)<<4)&65535
                value=(-raw)&65535 if sign&128 else raw
                self.assertEqual(independent(0,b,1,f5,sign)["de"],value)

    def test_pedal_threshold_exact_15_to_16(self):
        a=independent(15,200,5,250,127)
        b=independent(16,200,5,250,127)
        self.assertNotEqual(a["de"],b["de"])
        self.assertNotEqual(a["source"],b["source"])
        self.assertEqual(b["de"],0)

    def test_all_four_original_branches_covered_in_small_matrix(self):
        observed=set()
        for response in (0,15,16,255):
            for c in (0,1,255):
                observed.add(independent(response,40,c,250,128)["exit"])
        self.assertEqual(observed,{"skip_direct_726D",
                                   "zero_contribution_71FF",
                                   "skip_xrom_7225",
                                   "original_xrom_71FF"})

    def test_original_16bit_negative_displacement_wrap(self):
        positive=independent(0,255,1,255,0)["de"]
        negative=independent(0,255,1,255,128)["de"]
        self.assertEqual(negative,(-positive)&65535)

    def test_invalid_original_fields_and_untrusted_rom(self):
        for values in ((-1,0,0,0,0),(256,0,0,0,0),
                       (0,-1,0,0,0),(0,0,256,0,0),
                       (0,0,0,256,0),(0,0,0,0,-1)):
            with self.assertRaises(ValueError):independent(*values)
        with self.assertRaises(ValueError):
            original_z80(bytes(100),bytes(300),0,0,0,0,0)
        with self.assertRaisesRegex(ValueError,"authenticated master"):
            verify(bytes(0x90000),bytes(0x40000),0)

if __name__=="__main__":
    unittest.main()
