"""ROM-free original arcade Z80 74D8 counter and steering decay tests."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_74d8_steering_decay import (
    START,STOP,STAGE_SHA,independent,original_opcodes,verify
)


class OriginalSteering74D8Tests(unittest.TestCase):
    def test_fixed_original_cpu_stage_and_checksum(self):
        self.assertEqual((START,STOP),(0x74D8,0x7530))
        self.assertEqual(len(STAGE_SHA),64)

    def test_original_cpu_golden_outputs_for_both_decay_branches(self):
        cases=(
            ((0,0,0,0,0,0),(0,0,0,0,False,False)),
            ((8192,0,0,0,0,0),(1408,5632,64128,0,True,False)),
            ((8192,0,0,0,1,0),(5632,2816,59904,0,True,True)),
            ((12288,4660,44527,64188,3,0),(5048,47051,59140,2,True,True)),
            ((32768,65535,65535,1,128,1),(32768,49151,32769,127,False,True)),
            ((12288,4660,44527,64188,128,0),(5048,47051,59140,127,True,True)),
            ((12288,4660,44527,64188,129,0),(1262,49576,62926,129,True,False))
        )
        for args,expected in cases:
            result=independent(*args)
            self.assertEqual((result["final_de"],result["e769"],
                              result["e767"],result["car41"],
                              result["limited"],result["counter_decremented"]),
                             expected)
            self.assertEqual(result["next_pc"],STOP)

    def test_original_counter_signed_dec_around_0_1_128_129(self):
        for counter in range(256):
            result=independent(0x2000,0,0,0,counter,1)
            signed_dec=(counter-1)&255
            should_decrement=not bool(signed_dec&128)
            self.assertEqual(result["counter_decremented"],should_decrement)
            self.assertEqual(result["car41"],signed_dec if should_decrement else counter)

    def test_status_bit0_skips_signed_velocity_limiter(self):
        for bit in range(256):
            actual=independent(0x3000,0,0,0,0,bit)
            self.assertEqual(actual["selected_projection"],
                             0x3000 if bit&1 else 0x1600)
            self.assertEqual(actual["limited"],not bool(bit&1))

    def test_original_count_decrement_distributes_half_then_double(self):
        for selected in (0,1,2,3,0x7FFF,0x8000,0xFFFE,0xFFFF):
            r=independent(selected,0,0,0,1,1)
            signed=selected-65536 if selected>=32768 else selected
            half=(signed>>1)&65535
            self.assertEqual(r["final_de"],(half*2)&65535)
            self.assertEqual(r["e769"],half)
            self.assertEqual(r["e767"],(-2*half)&65535)

    def test_original_counter_hold_distributes_full_then_quarter(self):
        for selected in (0,1,2,3,0x7FFF,0x8000,0xFFFE,0xFFFF):
            r=independent(selected,0,0,0,0,1)
            signed=selected-65536 if selected>=32768 else selected
            quarter=(signed>>2)&65535
            self.assertEqual(r["final_de"],quarter)
            self.assertEqual(r["e769"],selected)
            self.assertEqual(r["e767"],(-quarter)&65535)
            self.assertEqual(r["car41"],0)

    def test_original_16bit_state_wrapping(self):
        for word in (0,1,0x7FFF,0x8000,0xFFFF):
            for heading in (0,1,0xFFFF):
                for counter in (0,1,128,129,255):
                    actual=independent(word,0xFFFF,word,heading,counter,1)
                    self.assertTrue(0<=actual["e769"]<65536)
                    self.assertTrue(0<=actual["e767"]<65536)
                    self.assertTrue(0<=actual["final_de"]<65536)

    def test_fail_closed_invalid_values_and_wrong_original_rom(self):
        for input_set in ((-1,0,0,0,0,0),(65536,0,0,0,0,0),
                          (0,0,0,0,256,0),(0,0,0,0,0,-1),
                          (0,0,0,65536,0,0)):
            with self.assertRaises(ValueError):independent(*input_set)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(8),0,0,0,0,0,0)
        with self.assertRaisesRegex(ValueError,"Authenticated"):
            verify(bytes(0x90000),0)


if __name__=="__main__":unittest.main()
