"""ROM-free tests for original arcade 7463 limiter + E767 angular motion."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_7463_correction_limit import (
    START,SKIP,STOP,STAGE_SHA,independent,original_opcodes,verify
)


class Steering7463LimiterTests(unittest.TestCase):
    def test_exact_original_stage_boundary(self):
        self.assertEqual((START,SKIP,STOP),(0x7463,0x748A,0x7499))
        self.assertEqual(len(STAGE_SHA),64)

    def test_independent_exact_original_golden_outputs(self):
        cases=(
            ((0,0,0,0),0,0,False),
            ((65535,0,0,0),65535,65535,False),
            ((0x1234,0,0xFFFF,0),0x1234,0x1233,False),
            ((0x8000,0xFFFF,0,0),0x8000,0x8000,False),
            ((0x3000,0x1234,0xADEF,0),5049,49576,True),
            ((0xFF00,0x8000,0x0102,0),0xFF00,0x0002,False),
            ((0x8000,0x1000,0xFFFF,1),0x8000,0x7FFF,False))
        for inputs,word,heading,limited in cases:
            actual=independent(*inputs)
            self.assertEqual((actual["car4c4d"],actual["heading_e767"],
                              actual["limited"]),(word,heading,limited))
            self.assertEqual(actual["next_pc"],STOP)

    def test_car_status_bit0_bypasses_original_speed_limit(self):
        for status in range(256):
            result=independent(0x3000,0x1234,0xADEF,status)
            self.assertEqual(result["limiter_bypassed"],bool(status&1))
            if status&1:
                self.assertEqual(result["car4c4d"],0x3000)
                self.assertFalse(result["limited"])

    def test_signed_motion_shift_and_third_rr_c_carry(self):
        # The last RR C carry reflects original motion bit2; omitting
        # it changes SBC HL,BC near the 0x9600 branch threshold.
        seen=set()
        for motion in (0,1,2,3,4,5,6,7,0x8000,0x8004,0xFFFF):
            x=independent(0x3000,motion,0,0)
            seen.add(x["car4c4d"])
            self.assertTrue(0<=x["heading_e767"]<=65535)
        self.assertGreater(len(seen),1)

    def test_heading_wrap_applies_original_chosen_word_not_raw_input(self):
        initial=0xFFFE
        result=independent(0x3000,0x1234,initial,0)
        self.assertEqual(result["heading_e767"],
                         (result["car4c4d"]+initial)&65535)

    def test_all_possible_low_car_status_values_no_unverified_branch(self):
        for word in (0,1,0x7FFF,0x8000,0xFFFF):
            for motion in (0,1,0x7FFF,0x8000,0xFFFF):
                for angle in (0,1,0xFFFF):
                    for status in range(256):
                        result=independent(word,motion,angle,status)
                        self.assertTrue(0<=result["car4c4d"]<=65535)
                        self.assertTrue(0<=result["heading_e767"]<=65535)

    def test_fail_closed_out_of_range_and_invalid_original_rom(self):
        for params in ((-1,0,0,0),(0,-1,0,0),(0,0,65536,0),
                       (0,0,0,256)):
            with self.assertRaises(ValueError):independent(*params)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x10),0,0,0,0)
        with self.assertRaisesRegex(ValueError,"Private checksum-verified"):
            verify(bytes(0x90000),0)


if __name__=="__main__":unittest.main()
