"""ROM-free tests for original bounded 2263 -> 22B8 -> 2360 AI chain."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_ai_entry_2263 import independent,UnverifiedAIExternal,START,END

def car(mode=0,active=True,source=100,car11=0,car23=1):
    b=bytearray(256)
    b[0xB3]=0 if active else 2
    b[0x7D]=mode;b[0xF7]=source
    b[0x91]=car11;b[0xA3]=car23;b[0xD7]=0xAA
    return bytes(b)

class OriginalAIEntryTests(unittest.TestCase):
    def run_model(self,record=None,e603=1,e627=6,ed59=0,linked_0e=20,linked_20=0):
        return independent(record if record is not None else car(),
                           e603,e627,ed59,linked_0e,linked_20,0,0)

    def test_original_bounded_span(self):
        self.assertEqual((START,END),(0x2263,0x22B8))

    def test_bit1_original_early_return_preserves_car(self):
        src=car(active=False)
        result=self.run_model(src,e603=0,ed59=0)
        self.assertEqual((result["exit"],result["car"]),("original_ret_nz",src))

    def test_original_selector_mismatch_bypasses_modification(self):
        src=car(mode=7)
        result=self.run_model(src)
        self.assertEqual(result["exit"],"opaque_jump_021A_no_update")
        self.assertEqual(result["car"],src)

    def test_matching_selector_composes_original_pedal_and_event_chain(self):
        # E627=6 -> ((6&0x0e)>>1)-3 == 0
        result=self.run_model(car(mode=0,source=100),e627=6)
        self.assertEqual(result["exit"],"verified_ai_path_then_opaque_021A")
        self.assertEqual(result["car"][0xD7],(100>>1)&0x7E)
        self.assertTrue(result["event_reason"])

    def test_selector_underflows_as_original_unsigned_byte(self):
        result=self.run_model(car(mode=253,source=64),e627=0)
        self.assertEqual(result["exit"],"verified_ai_path_then_opaque_021A")

    def test_original_31e6_call_raises_explicit_unknown(self):
        with self.assertRaisesRegex(UnverifiedAIExternal,"31E6"):
            self.run_model(car(car11=100,car23=0),e603=0,ed59=0)

    def test_original_1190_ix_reassignment_raises_explicit_unknown(self):
        with self.assertRaisesRegex(UnverifiedAIExternal,"1190"):
            self.run_model(car(mode=4),e627=14)
        self.assertEqual(self.run_model(car(mode=4),e627=30)["exit"],
                         "verified_ai_path_then_opaque_021A")

    def test_original_inputs_fail_closed(self):
        with self.assertRaises(ValueError):self.run_model(bytes(255))
        with self.assertRaises(ValueError):self.run_model(e627=256)

if __name__=="__main__":unittest.main()
