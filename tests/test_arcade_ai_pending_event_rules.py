"""ROM-free regressions: authenticated original AI pending-event bit rules."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_ai_pending_event_rules import (
    independent,opcode,START,END,STATUS_31,STATUS_32,PEDAL_RESPONSE,
    COMPARE_BYTE,PENDING_EVENTS,LINK_GATE,
)

def car(status31=0,status32=0,drive=0,compare=0,link=0,events=0xF0):
    b=bytearray(256)
    b[STATUS_31],b[STATUS_32]=status31,status32
    b[PEDAL_RESPONSE],b[COMPARE_BYTE]=drive,compare
    b[LINK_GATE],b[PENDING_EVENTS]=link,events
    return bytes(b)

class OriginalAIPendingEventTests(unittest.TestCase):
    def test_exact_original_stage(self):
        self.assertEqual((START,END),(0x230B,0x2361))

    def test_restricted_thresholds(self):
        for n in (0,8):self.assertEqual(independent(car(status31=16,compare=n),0)[0],"event_bit1")
        self.assertEqual(independent(car(status31=16,compare=9),0)[0],"threshold_no_event")
        self.assertEqual(independent(car(status31=16,compare=24),0)[0],"event_bit2")

    def test_three_drive_threshold_tiers(self):
        self.assertEqual(independent(car(drive=0x44,compare=50),0)[0],"threshold_no_event")
        self.assertEqual(independent(car(drive=0x44,compare=80),0)[0],"event_bit2")
        self.assertEqual(independent(car(drive=0x43,compare=49),0)[0],"event_bit1")
        self.assertEqual(independent(car(drive=0x3B,compare=71),0)[0],"event_bit1")
        self.assertEqual(independent(car(drive=0x3B,compare=72),0)[0],"threshold_no_event")
        self.assertEqual(independent(car(drive=0x3B,compare=128),0)[0],"event_bit2")

    def test_original_linked_state_gate_and_its_exclusions(self):
        base=car(drive=0x44,compare=80,link=16)
        self.assertEqual(independent(base,2)[0],"linked_gate_suppressed")
        self.assertEqual(independent(base,3)[0],"event_bit2")
        self.assertEqual(independent(car(drive=0x44,compare=80),2)[0],"event_bit2")
        self.assertEqual(independent(car(status31=16,compare=24,link=16),2)[0],"event_bit2")

    def test_only_one_bit_added_to_pending_event_field(self):
        for original in (0,0x80,0xF0,0xFE):
            for value in (1,50,80,128):
                item=car(drive=0x44,compare=value,events=original)
                _,changed=independent(item,3)
                self.assertEqual(changed[PENDING_EVENTS]&original,original)
                self.assertIn(changed[PENDING_EVENTS]^original,(0,2,4))

    def test_unrelated_record_fields_unchanged(self):
        source=bytearray(car(compare=0,events=0))
        source[0x40]=0xAA
        _,changed=independent(bytes(source),0)
        self.assertEqual(changed[0x40],0xAA)
        self.assertEqual({i for i in range(256) if changed[i]!=source[i]},
                         {PENDING_EVENTS})

    def test_bad_data_or_forged_reference_exits(self):
        for n in (-1,256):
            with self.assertRaises(ValueError):independent(car(),n)
        with self.assertRaises(ValueError):independent(bytes(255),0)
        with self.assertRaises(ValueError):opcode(bytes(0x90000),car(),0)

if __name__=="__main__":unittest.main()
