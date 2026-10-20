"""Synthetic ROM-free regression for original arcade 021A candidate comparison.

Private ROM and contact metric lookup table are deliberately not in CI.
The checker at tools/arcade_ai_distance_table.py can replay real original
opcodes only when run locally with the user's authenticated original master.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_ai_distance_table import (
    independent,opcode,magnitude,START,STOP,TABLE_BASE,
)

def fake_master()->bytes:
    m=bytearray(0x90000)
    for i in range(256):m[TABLE_BASE+2*i+1]=(i*13+7)&255
    return bytes(m)

def car(x=10,y=20,x1=10,y1=20,x2=10,y2=20,skip=0):
    b=bytearray(256)
    b[0x01],b[0x0B]=x,y
    b[0xC6],b[0xC7],b[0xC8],b[0xC9]=x1,y1,x2,y2
    b[0xB3]=skip
    return bytes(b)

class OriginalMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.master=fake_master()

    def test_original_span_and_private_table_location(self):
        self.assertEqual((START,STOP,TABLE_BASE),(0x021A,0x028D,0xA000))

    def test_saturated_wrapped_magnitude_boundaries(self):
        self.assertEqual([magnitude(x,0) for x in (0,1,15,16,127,128,129,255)],
                         [0,1,15,15,15,15,15,1])

    def test_first_and_second_table_indices_are_distinct(self):
        r=independent(self.master,car(x=0,y=0,x1=1,y1=1,x2=2,y2=2))
        self.assertEqual(r["first"],(0x11*13+7)&255)
        self.assertEqual(r["second"],(0x22*13+7)&255)
        self.assertEqual(r["hl"],TABLE_BASE+2*0x22+1)

    def test_clamped_distance_index_with_8bit_wrap(self):
        r=independent(self.master,car(x=0,y=0,x1=255,y1=0,x2=128,y2=0))
        self.assertEqual(r["first"],(1*13+7)&255)
        self.assertEqual(r["second"],(15*13+7)&255)

    def test_equal_candidates_tie_to_original_not_carry_path(self):
        r=independent(self.master,car(x1=11,y1=20,x2=11,y2=20))
        self.assertEqual(r["exit"],"branch_02C3")
        self.assertTrue(r["zero"])
        self.assertFalse(r["carry"])

    def test_original_event_bit2_skips_lookup_entirely(self):
        self.assertEqual(independent(self.master,car(skip=4)),{"exit":"external_05DC"})

    def test_raw_second_differences_wrap_unsigned_byte(self):
        r=independent(self.master,car(x=255,y=0,x1=0,y1=0,x2=0,y2=255))
        self.assertEqual((r["b"],r["c"]),(1,255))

    def test_invalid_original_source_or_short_record_rejected(self):
        with self.assertRaises(ValueError):independent(self.master,bytes(255))
        with self.assertRaises(ValueError):independent(bytes(9),car())
        with self.assertRaises(ValueError):opcode(bytes(9),car())
        with self.assertRaises(ValueError):magnitude(-1,0)

if __name__=="__main__":unittest.main()
