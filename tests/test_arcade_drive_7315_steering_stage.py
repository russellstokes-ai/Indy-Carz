"""ROM-free regression for authentic original master Z80 7315 steering."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_7315_steering_stage import (
    START,STOP,NORMAL,STAGE_SHA,independent,original_z80,verify,
)


class OriginalSteering7315Tests(unittest.TestCase):
    def test_original_stage_bounds(self):
        self.assertEqual((START,STOP,NORMAL),(0x7315,0x7376,0x7530))
        self.assertEqual(len(STAGE_SHA),64)

    def test_first_original_low_threshold_branches_before_other_inputs(self):
        for initial in (0,1,0xFF):
            actual=independent(initial,0xFFFF,0x0403,0xEFAB,34)
            self.assertEqual(actual,{
                "branch":"low_E771_to_7376","next_pc":0x7376,
                "e767":0xEFAB,"car4c4d":0x0403,"addresses":()})

    def test_second_original_low_threshold_reads_car_seventy_one(self):
        for e773 in (0,1,0xFF):
            actual=independent(0x0100,e773,0x1234,0xEFAB,221)
            self.assertEqual(actual,{
                "branch":"low_E773_to_7381","next_pc":0x7381,
                "e767":0xEFAB,"car4c4d":0x1234,"addresses":(),"a":221})

    def test_original_0402_lower_clamp_boundary(self):
        keep=independent(0x100,0x100,0x0402,0xEFAB,127)
        bounded=independent(0x100,0x100,0x0403,0xEFAB,127)
        self.assertEqual(keep["branch"],"passthrough")
        self.assertEqual(bounded["branch"],"positive_clamp")
        self.assertEqual((keep["car4c4d"],bounded["car4c4d"]),(896,896))
        self.assertEqual(keep["addresses"],(0x0470,0x0170))
        self.assertEqual(bounded["addresses"],(0x0470,0x0070))

    def test_original_negative_bound_is_exclusive_due_to_previous_carry(self):
        last_clamped=independent(0x100,0x100,0xFBFD,0xEFAB,127)
        first_passthrough=independent(0x100,0x100,0xFBFE,0xEFAB,127)
        self.assertEqual(last_clamped["branch"],"negative_clamp")
        self.assertEqual(first_passthrough["branch"],"passthrough")
        self.assertEqual(last_clamped["car4c4d"],0xFC80)
        self.assertEqual(first_passthrough["car4c4d"],0xFC7E)
        self.assertEqual(last_clamped["addresses"],(0xFC70,0x0070))
        self.assertEqual(first_passthrough["addresses"],(0xFB70,0x7F70))

    def test_16bit_heading_update_adds_original_clamped_signed_increment(self):
        for original in (0,0xEFAB,0xFFFF):
            p=independent(0x100,0x100,0x0403,original,0)
            n=independent(0x100,0x100,0x8000,original,0)
            self.assertEqual(p["e767"],(original+0x0380)&65535)
            self.assertEqual(n["e767"],(original+0xFC80)&65535)
            self.assertEqual(p["next_pc"],NORMAL)
            self.assertEqual(n["next_pc"],NORMAL)

    def test_no_steering_input_preserves_heading(self):
        r=independent(0x100,0x100,0,0xEFAB,0)
        self.assertEqual((r["car4c4d"],r["e767"]),(0,0xEFAB))

    def test_32bit_host_math_must_not_leak_into_z80_signed_values(self):
        for original in (0,1,0xFFFF):
            for heading in (0,1,0x7FFF,0x8000,0xFBFE,0xFFFF):
                actual=independent(0x100,0x100,original,heading,255)
                self.assertTrue(0<=actual["e767"]<=65535)
                self.assertTrue(0<=actual["car4c4d"]<=65535)

    def test_exhaustive_original_car_input_domain_in_independent_model(self):
        branches=set()
        for word in range(65536):
            result=independent(0x100,0x100,word,0,0)
            branches.add(result["branch"])
            self.assertTrue(0<=result["car4c4d"]<=65535)
        self.assertEqual(branches,{"passthrough","positive_clamp","negative_clamp"})

    def test_invalid_input_or_untrusted_reference_rom_rejected(self):
        for args in ((-1,0,0,0,0),(0,65536,0,0,0),
                     (0,0,-1,0,0),(0,0,0,65536,0),(0,0,0,0,256)):
            with self.assertRaises(ValueError):independent(*args)
        with self.assertRaises(ValueError):
            original_z80(bytes(4),bytes(6),0,0,0,0,0)
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            verify(bytes(0x90000),bytes(0x40000),0)


if __name__=="__main__":
    unittest.main()
