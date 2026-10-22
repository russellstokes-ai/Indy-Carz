"""ROM-free regressions for original 31E6 race-start global gate and 0A4F."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_race_start_gate_31e6 import SIGNATURES, independent, actual_opcodes, verify


class OriginalRaceStartGateTests(unittest.TestCase):
    def test_source_contains_original_prestart_call(self):
        self.assertEqual(SIGNATURES[0][:2],(0x31E6,0x31E9))
        self.assertEqual(SIGNATURES[1][:2],(0x31E9,0x3208))
        self.assertEqual(SIGNATURES[2][:2],(0x0A4F,0x0A5E))

    def test_both_global_bytes_zero_early_return(self):
        result=independent(0,0,79,0x1234,222)
        self.assertEqual(result,{
            "e61f":0,"e69f":0,"e67b":0,"e67c":79,
            "car91":222,"accumulator":0,"exit":"early_ret_31FA",
        })

    def test_nonzero_e603_starts_regardless_of_old_e67b(self):
        for flag in (1,128,255):
            result=independent(flag,0,83,0,40)
            self.assertEqual(result["exit"],"continue_3208")
            self.assertEqual((result["e67b"],result["e67c"]),(31,1))

    def test_nonzero_e67b_starts_when_e603_zero(self):
        for flag in (1,127,255):
            result=independent(0,flag,111,1,2)
            self.assertEqual((result["e67b"],result["e67c"]),(31,1))
            self.assertEqual(result["car91"],1)

    def test_original_helper_subtracts_only_low_ed59(self):
        self.assertEqual(independent(1,0,0,0x0101,10)["car91"],9)
        self.assertEqual(independent(1,0,0,0xFF01,10)["car91"],9)
        self.assertEqual(independent(1,0,0,0xFFFF,0)["car91"],1)
        self.assertEqual(independent(1,0,0,0xFE00,123)["car91"],123)

    def test_e61f_e69f_always_cleared(self):
        for e603,e67b in ((0,0),(0,1),(1,0),(255,255)):
            result=independent(e603,e67b,20,0x5432,100)
            self.assertEqual((result["e61f"],result["e69f"]),(0,0))

    def test_returned_a_one_after_helper_af_restore(self):
        result=independent(1,0,200,0xFFF0,25)
        self.assertEqual(result["accumulator"],1)
        self.assertEqual(result["car91"],(25-0xF0)&255)

    def test_reject_invalid_byte_or_word(self):
        for args in ((-1,0,0,0,0),(0,256,0,0,0),(0,0,256,0,0),
                     (1,0,0,65536,0),(1,0,0,0,256)):
            with self.assertRaises(ValueError):independent(*args)

    def test_untrusted_original_fails_closed(self):
        with self.assertRaises(ValueError):
            actual_opcodes(bytes(0x90000),0,0,0,0,0)
        with self.assertRaisesRegex(ValueError,"Authenticated original"):
            verify(bytes(0x90000),0)


if __name__=="__main__":
    unittest.main()
