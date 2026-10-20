"""ROM-free regression for original AI linked IY countdown and spatial gates."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_ai_linked_countdown import (
    independent,opcode,START,STOP,BIT4_7E,BIT4_31,BIT7_32,
    FIRST_AXIS,SECOND_AXIS,GATE_5C,PENDING,
)

def car(bit7e=0,bit31=0,bit32=0,x=40,y=50,gate=0,event=0):
    b=bytearray(256)
    b[BIT4_7E]=bit7e;b[BIT4_31]=bit31;b[BIT7_32]=bit32
    b[FIRST_AXIS]=x;b[SECOND_AXIS]=y;b[GATE_5C]=gate;b[PENDING]=event
    return bytes(b)

class OriginalAILinkedCountdownTests(unittest.TestCase):
    def test_stage(self):
        self.assertEqual((START,STOP),(0x22B8,0x230B))

    def test_forced_event_clears_linked_timer(self):
        r=independent(car(bit7e=16),200,3,0,0)
        self.assertEqual((r["reason"],r["linked_0e"],r["car"][PENDING]),
                         ("forced_event_bit1",0,2))
        self.assertTrue(r["linked_changed"])

    def test_force_requires_exact_original_flags(self):
        for item in (car(bit7e=0),car(bit7e=16,bit31=16),car(bit7e=16,bit32=128)):
            r=independent(item,100,3,0,0)
            self.assertEqual(r["reason"],"timer_active")

    def test_linked_counter_zero_falls_through_without_write(self):
        r=independent(car(x=40,y=50,gate=2),0,1,0x6428,0x6432)
        self.assertEqual(r["reason"],"bounded_gate_event_bit1")
        self.assertEqual(r["linked_0e"],0)
        self.assertFalse(r["linked_changed"])

    def test_positive_countdown_decrements_and_returns(self):
        for before,after in ((1,0),(2,1),(128,127)):
            r=independent(car(),before,0,0,0)
            self.assertEqual((r["reason"],r["linked_0e"]),("timer_active",after))

    def test_original_signed_dec_above_128_bypasses_timer_return(self):
        r=independent(car(),129,0,0,0)
        self.assertNotEqual(r["reason"],"timer_active")
        self.assertEqual(r["linked_0e"],129)

    def test_half_open_original_coordinate_windows(self):
        for x,y,expected in ((19,40,False),(21,41,True),(39,59,True),
                             (40,41,False),(21,60,False)):
            r=independent(car(x=x,y=y,gate=2),0,0,0x2814,0x3C28)
            self.assertEqual(r["reason"]=="bounded_gate_event_bit1",expected)

    def test_fallback_composes_original_event_thresholds(self):
        r=independent(car(x=200,y=200),0,0,0x2010,0x2010)
        self.assertTrue(r["reason"].startswith("fallback_"))

    def test_bad_data_and_fake_rom_fail_closed(self):
        with self.assertRaises(ValueError):independent(bytes(255),0,0,0,0)
        with self.assertRaises(ValueError):independent(car(),0,0,-1,0)
        with self.assertRaises(ValueError):opcode(bytes(0x90000),car(),0,0,0,0)

if __name__=="__main__":unittest.main()
